import asyncio
import struct
from contextlib import asynccontextmanager

import pytest
from aiohttp import ClientSession, WSServerHandshakeError, web, WSMsgType
from server import create_app, DiagnosticPad


@asynccontextmanager
async def running(pads=None, **kwargs):
    pads = pads or [DiagnosticPad() for _ in range(4)]
    runner = web.AppRunner(create_app(pads, 'secret', **kwargs))
    await runner.setup()
    site = web.TCPSite(runner, '127.0.0.1', 0)
    await site.start()
    url = f'http://127.0.0.1:{site._server.sockets[0].getsockname()[1]}'
    try:
        async with ClientSession() as session:
            yield session, url, pads
    finally:
        await runner.cleanup()


async def receive(ws, kind):
    async with asyncio.timeout(2):
        while True:
            data = await ws.receive_json()
            if data['type'] == kind:
                return data


async def state(ws, button):
    await ws.send_json({'type': 'state', 'buttons': [button], 'axes': [0]*4, 'triggers': [0]*2})
    await ws.send_json({'type': 'ping', 'time': 123})
    assert (await receive(ws, 'pong'))['time'] == 123


def test_cli_exposes_bounded_controller_capacity():
    import subprocess
    import sys
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    help_result = subprocess.run([sys.executable, str(root/'server.py'), '--help'], capture_output=True, text=True)
    assert '--controllers {1,2,3,4}' in help_result.stdout
    invalid = subprocess.run([sys.executable, str(root/'server.py'), '--controllers', '5'], capture_output=True, text=True)
    assert invalid.returncode == 2


def test_single_pad_factory_defaults_to_four_and_validates_capacity():
    created = []
    def factory():
        pad = DiagnosticPad()
        created.append(pad)
        return pad
    first = DiagnosticPad()
    app = create_app(first, 'secret', pad_factory=factory)
    assert app is not None
    assert len(created) == 3
    for capacity in (0, 5, True):
        with pytest.raises(ValueError):
            create_app(first, 'secret', capacity=capacity)


@pytest.mark.asyncio
@pytest.mark.parametrize('query,origin,expected', [
    ('token=wrong', None, 401), ('token=%C3%A9', None, 401),
    ('token=secret', 'https://evil.invalid', 403),
    ('token=secret&slot=0', None, 400), ('token=secret&slot=5', None, 400),
])
async def test_handshake_fails_closed(query, origin, expected):
    async with running() as (session, url, pads):
        with pytest.raises(WSServerHandshakeError) as exc:
            await session.ws_connect(url + '/ws?' + query, origin=origin)
        assert exc.value.status == expected
        assert (await (await session.get(url + '/api/status')).json())['connected_count'] == 0


@pytest.mark.asyncio
async def test_watchdog_resets_once_and_keepalive_is_per_slot():
    class CountingPad(DiagnosticPad):
        resets = 0
        def reset(self):
            self.resets += 1
            super().reset()
    pads = [CountingPad() for _ in range(4)]
    async with running(pads) as (session, url, _):
        a = await session.ws_connect(url + '/ws?token=secret&slot=1')
        b = await session.ws_connect(url + '/ws?token=secret&slot=2')
        await receive(a, 'ready')
        await receive(b, 'ready')
        await state(a, 'cross')
        for _ in range(10):
            await state(b, 'circle')
            await asyncio.sleep(.1)
        assert pads[0].resets == 1
        assert pads[0].state['buttons'] == []
        assert pads[1].resets == 0
        await state(a, 'square')
        await asyncio.sleep(.7)
        assert pads[0].resets == 2
        await a.close()
        await b.close()


@pytest.mark.asyncio
async def test_binary_immediate_apply_sparse_ack_and_no_compression():
    async with running() as (session, url, pads):
        ws = await session.ws_connect(url + '/ws?token=secret&slot=3', compress=15)
        await receive(ws, 'ready')
        assert ws.compress == 0
        await ws.send_bytes(struct.pack('<HhhhhBBI', 1, 32767, -32767, 0, 0, 255, 0, 30))
        ack = await receive(ws, 'ack')
        assert ack['seq'] == 30 and ack['server_ms'] >= 0
        assert pads[2].state == {'buttons':['cross'], 'axes':[1,-1,0,0], 'triggers':[1,0]}
        await ws.send_bytes(struct.pack('<HhhhhBBI', 2, 0, 0, 0, 0, 0, 0, 31))
        await ws.send_json({'type':'ping', 'time':99})
        assert (await ws.receive_json()) == {'type':'pong', 'time':99}
        assert pads[2].state['buttons'] == ['circle']
        await ws.close()


@pytest.mark.asyncio
async def test_switch_conflict_retains_owner_and_switch_neutralizes():
    async with running() as (session, url, pads):
        a = await session.ws_connect(url + '/ws?token=secret&slot=1')
        await receive(a, 'ready')
        b = await session.ws_connect(url + '/ws?token=secret&slot=2')
        await receive(b, 'ready')
        await state(a, 'cross')
        await a.send_json({'type': 'select', 'slot': 2})
        assert (await receive(a, 'error'))['code'] == 'slot_busy'
        assert pads[0].state['buttons'] == ['cross']
        await a.send_json({'type': 'select', 'slot': 4})
        assert (await receive(a, 'ready'))['slot'] == 4
        assert pads[0].state['buttons'] == []
        await state(a, 'home')
        assert pads[3].state['buttons'] == ['home']
        await a.close()
        await b.close()


@pytest.mark.asyncio
@pytest.mark.parametrize('payload,code', [
    (b'', 1008), (bytes(15), 1008), (bytes(17), 1008),
    (struct.pack('<HhhhhBBI', 0x8000, 0,0,0,0,0,0,0), 1008),
    (struct.pack('<HhhhhBBI', 0, 0,-32768,0,0,0,0,0), 1008),
    (bytes(4097), 1009), ('{bad json', 1008),
])
async def test_invalid_input_closes_only_owner_and_neutralizes(payload, code):
    async with running() as (session, url, pads):
        a = await session.ws_connect(url + '/ws?token=secret&slot=1')
        b = await session.ws_connect(url + '/ws?token=secret&slot=2')
        await receive(a, 'ready')
        await receive(b, 'ready')
        await state(a, 'cross')
        await state(b, 'circle')
        if isinstance(payload, bytes):
            await a.send_bytes(payload)
        else:
            await a.send_str(payload)
        async with asyncio.timeout(2):
            while True:
                msg = await a.receive()
                if msg.type == WSMsgType.CLOSE:
                    assert msg.data == code
                    break
        await a.close()
        await state(b, 'circle')
        assert pads[0].state['buttons'] == []
        assert pads[1].state['buttons'] == ['circle']
        data = await (await session.get(url + '/api/status')).json()
        assert data['connected_count'] == 1
        await b.close()


@pytest.mark.asyncio
async def test_simultaneous_slot_reservation_has_exactly_one_winner():
    async with running() as (session, url, pads):
        results = await asyncio.gather(*(session.ws_connect(url + '/ws?token=secret&slot=4') for _ in range(8)), return_exceptions=True)
        winners = [r for r in results if not isinstance(r, Exception)]
        assert len(winners) == 1
        assert all(r.status == 409 for r in results if isinstance(r, Exception))
        assert (await receive(winners[0], 'ready'))['slot'] == 4
        await winners[0].close()


@pytest.mark.asyncio
async def test_shutdown_closes_live_clients_without_waiting_for_timeout():
    pads = [DiagnosticPad() for _ in range(4)]
    app = create_app(pads, 'secret')
    socket_options = []
    async def prepared(request, response):
        import socket
        sock = request.transport.get_extra_info('socket')
        socket_options.append(sock.getsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY))
    app.on_response_prepare.append(prepared)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '127.0.0.1', 0)
    await site.start()
    port = site._server.sockets[0].getsockname()[1]
    try:
        async with ClientSession() as session:
            ws = await session.ws_connect(f'http://127.0.0.1:{port}/ws?token=secret')
            await receive(ws, 'ready')
            await state(ws, 'cross')
            assert socket_options == [1]
            async def accept_close():
                while (await ws.receive()).type not in (WSMsgType.CLOSE, WSMsgType.CLOSED):
                    pass
                await ws.close()
            async with asyncio.timeout(2):
                await asyncio.gather(runner.cleanup(), accept_close())
            assert pads[0].state['buttons'] == []
    finally:
        await runner.cleanup()


@pytest.mark.asyncio
async def test_remote_status_hides_token_and_pad_state():
    from aiohttp import TCPConnector
    async with running() as (_, url, pads):
        async with ClientSession(connector=TCPConnector(local_addr=('127.0.0.2', 0))) as remote:
            response = await remote.get(url + '/api/status')
            body = await response.text()
            data = await response.json()
            assert 'secret' not in body and 'url' not in data
            assert 'state' not in data and 'packets' not in data
            assert len(data['slots']) == 4
            assert all('state' not in row and 'packets' not in row for row in data['slots'])
            assert (await remote.get(url + '/api/qr')).status == 403
            assert (await remote.get(url + '/host')).status == 403


@pytest.mark.asyncio
async def test_four_independent_exclusive_slots_and_release():
    async with running() as (session, url, pads):
        clients = []
        for i in range(4):
            ws = await session.ws_connect(url + '/ws?token=secret')
            ready = await receive(ws, 'ready')
            assert ready['slot'] == i + 1
            assert ready['capacity'] == 4
            assert ready['connected_count'] == i + 1
            clients.append(ws)
        with pytest.raises(WSServerHandshakeError) as exc:
            await session.ws_connect(url + '/ws?token=secret&slot=1')
        assert exc.value.status == 409
        for ws, button in zip(clients, ['cross', 'circle', 'square', 'triangle']):
            await state(ws, button)
        assert [p.state['buttons'] for p in pads] == [['cross'], ['circle'], ['square'], ['triangle']]
        data = await (await session.get(url + '/api/status')).json()
        assert data['connected_count'] == 4
        assert [s['packets'] for s in data['slots']] == [1]*4
        await clients[1].close()
        roster = await receive(clients[3], 'roster')
        assert roster['connected_count'] == 3
        assert pads[1].state['buttons'] == []
        ws = await session.ws_connect(url + '/ws?token=secret')
        assert (await receive(ws, 'ready'))['slot'] == 2
        await ws.close()
        for ws in clients:
            await ws.close()
