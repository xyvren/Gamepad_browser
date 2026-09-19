import asyncio
import pytest
from aiohttp import web, ClientSession, WSServerHandshakeError

@pytest.mark.asyncio
async def test_pair_input_exclusive_disconnect_and_timeout():
    from server import create_app, DiagnosticPad
    pad = DiagnosticPad()
    app = create_app(pad, 'secret')
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '127.0.0.1', 0)
    await site.start()
    port = site._server.sockets[0].getsockname()[1]
    url = f'http://127.0.0.1:{port}'
    try:
        async with ClientSession() as s:
            with pytest.raises(WSServerHandshakeError):
                await s.ws_connect(url+'/ws?token=wrong')
            ws = await s.ws_connect(url+'/ws?token=secret')
            assert (await ws.receive_json())['type']=='ready'
            with pytest.raises(WSServerHandshakeError):
                await s.ws_connect(url+'/ws?token=secret&slot=1')
            await ws.send_json({'type':'state','buttons':['cross'],'axes':[0.5,0,0,0],'triggers':[1,0]})
            await asyncio.sleep(.05)
            assert pad.state['buttons']==['cross']
            await asyncio.sleep(.7)
            assert pad.state['buttons']==[]
            await ws.send_json({'type':'state','buttons':['square'],'axes':[0,0,0,0],'triggers':[0,0]})
            await asyncio.sleep(.05)
            await ws.close()
            await asyncio.sleep(.05)
            assert pad.state['buttons']==[]
            r=await s.get(url+'/api/status')
            assert (await r.json())['mode']=='diagnostic'
    finally:
        await runner.cleanup()
