import argparse
import asyncio
import hmac
import io
import json
import secrets
import socket
import time
from pathlib import Path
from aiohttp import web
import qrcode
from protocol import decode_binary, neutral, validate_state

import sys
ROOT = Path(getattr(sys, '_MEIPASS', Path(__file__).parent))

class DiagnosticPad:
    mode = 'diagnostic'
    error = 'Driver ViGEmBus belum tersedia. Input terlihat di dashboard, tetapi belum masuk ke game.'
    def __init__(self):
        self.state = neutral()
        self.rumble_cb = None
    def apply(self, state): self.state = state
    def reset(self): self.apply(neutral())
    def set_rumble_callback(self, cb): self.rumble_cb = cb
    def trigger_rumble(self, large, small):
        if self.rumble_cb:
            self.rumble_cb(large, small)

class XboxPad(DiagnosticPad):
    mode = 'xinput'
    error = ''
    def __init__(self):
        import vgamepad as vg
        self.vg = vg
        self.device = vg.VX360Gamepad()
        super().__init__()
        names = {'cross':'A','circle':'B','square':'X','triangle':'Y','up':'DPAD_UP','down':'DPAD_DOWN','left':'DPAD_LEFT','right':'DPAD_RIGHT','l1':'LEFT_SHOULDER','r1':'RIGHT_SHOULDER','l3':'LEFT_THUMB','r3':'RIGHT_THUMB','share':'BACK','options':'START','home':'GUIDE'}
        self.buttons = {k:getattr(vg.XUSB_BUTTON,'XUSB_GAMEPAD_'+v) for k,v in names.items()}
        def _on_notification(client, target, large_motor, small_motor, led_number, user_data):
            self.trigger_rumble(large_motor, small_motor)
        try:
            self.device.register_notification(_on_notification)
        except Exception:
            pass
    def apply(self, state):
        self.device.reset()
        for b in state['buttons']: self.device.press_button(button=self.buttons[b])
        x,y,rx,ry = state['axes']
        self.device.left_joystick_float(x_value_float=x,y_value_float=-y)
        self.device.right_joystick_float(x_value_float=rx,y_value_float=-ry)
        self.device.left_trigger_float(value_float=state['triggers'][0])
        self.device.right_trigger_float(value_float=state['triggers'][1])
        self.device.update()
        self.state = state

def lan_ip():
    s = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
    try:
        s.connect(('192.0.2.1',80))
        return s.getsockname()[0]
    except OSError: return '127.0.0.1'
    finally: s.close()

def create_app(pad, token, port=8765, *, pad_factory=None, capacity=4, https_port=8766):
    """Application slots are stable pad identities, not Windows XInput indices.

    Supply an ordered list of 1..4 pads, or a first pad plus a factory for
    the remaining slots (defaults to the first pad's class).
    """
    if type(capacity) is not int or not 1 <= capacity <= 4:
        raise ValueError('Capacity must be between one and four')
    app = web.Application(client_max_size=4096)
    if isinstance(pad, (list, tuple)):
        pads = list(pad)
    else:
        factory = pad_factory or type(pad)
        pads = [pad] + [factory() for _ in range(capacity - 1)]
    if not 1 <= len(pads) <= 4 or len({id(p) for p in pads}) != len(pads):
        raise ValueError('Provide one to four distinct pads')
    slots = [{'pad': p, 'ws': None, 'last': 0.0, 'count': 0, 'armed': False} for p in pads]
    pad = pads[0]

    for s in slots:
        def make_handler(slot_item):
            def on_rumble(large, small):
                ws = slot_item['ws']
                if ws is not None and not ws.closed and ws.prepared:
                    try:
                        loop = asyncio.get_running_loop()
                    except RuntimeError:
                        return
                    async def send():
                        try:
                            await ws.send_json({'type': 'rumble', 'large': large, 'small': small})
                        except Exception:
                            pass
                    loop.call_soon_threadsafe(lambda: asyncio.create_task(send()))
            return on_rumble
        s['pad'].set_rumble_callback(make_handler(s))

    def roster(detail=False):
        rows = []
        for i, item in enumerate(slots, 1):
            row = {'slot': i, 'connected': item['ws'] is not None, 'mode': item['pad'].mode}
            if detail:
                row.update(state=item['pad'].state, packets=item['count'])
            rows.append(row)
        return {'connected_count': sum(s['ws'] is not None for s in slots),
                'capacity': len(slots), 'slots': rows}

    async def broadcast():
        data = {'type': 'roster', **roster()}
        clients = [s['ws'] for s in slots if s['ws'] is not None and s['ws'].prepared and not s['ws'].closed]
        if clients:
            await asyncio.gather(*(w.send_json(data) for w in clients), return_exceptions=True)
    def authorized(request):
        supplied = request.query.get('token', '')
        return supplied.isascii() and hmac.compare_digest(supplied, token)
    def local(request): return request.remote in ('127.0.0.1','::1')
    async def index(request): return web.FileResponse(ROOT/'static'/'index.html')
    async def host(request):
        if not local(request): raise web.HTTPForbidden(text='Dashboard hanya tersedia di desktop server.')
        return web.FileResponse(ROOT/'static'/'host.html')
    async def status(request):
        data={'mode':pad.mode,'error':pad.error,'connected':any(s['ws'] is not None for s in slots), **roster(local(request))}
        if local(request):
            ip = lan_ip()
            data.update(
                url=f'http://{ip}:{port}/#token={token}',
                https_url=f'https://{ip}:{https_port}/#token={token}',
                state=pad.state,
                packets=sum(s['count'] for s in slots)
            )
        return web.json_response(data,headers={'Cache-Control':'no-store'})
    async def qr(request):
        if not local(request): raise web.HTTPForbidden()
        buf=io.BytesIO()
        proto = request.query.get('proto', 'http')
        p = https_port if proto == 'https' else port
        qrcode.make(f'{proto}://{lan_ip()}:{p}/#token={token}').save(buf,format='PNG')
        return web.Response(body=buf.getvalue(),content_type='image/png',headers={'Cache-Control':'no-store'})
    async def ws_handler(request):
        if not authorized(request): raise web.HTTPUnauthorized(text='Pairing tidak valid. Scan QR dari desktop.')
        origin=request.headers.get('Origin')
        if origin and origin not in (f'http://{request.host}',f'https://{request.host}'): raise web.HTTPForbidden()
        requested = request.query.get('slot')
        if requested is not None and requested not in [str(i) for i in range(1, len(slots)+1)]:
            raise web.HTTPBadRequest(text='Invalid slot')
        state = slots[int(requested)-1] if requested else next((s for s in slots if s['ws'] is None), None)
        if state is None or state['ws'] is not None:
            raise web.HTTPConflict(text='Controller sedang digunakan.')
        ws=web.WebSocketResponse(heartbeat=10,max_msg_size=4096,compress=False)
        state['ws']=ws  # Reserve synchronously, before the handshake yields.
        current_pad = state['pad']
        try:
            await ws.prepare(request)
            state['last']=time.monotonic()
            await ws.send_json({'type':'ready','slot':slots.index(state)+1,'mode':current_pad.mode,'message':current_pad.error, **roster()})
            await broadcast()
            async for msg in ws:
                if msg.type not in (web.WSMsgType.TEXT, web.WSMsgType.BINARY): continue
                try:
                    started = time.perf_counter()
                    if msg.type == web.WSMsgType.BINARY:
                        value, seq = decode_binary(msg.data)
                        current_pad.apply(value)
                        elapsed = (time.perf_counter() - started) * 1000
                        state['last'] = time.monotonic()
                        state['armed'] = True
                        state['count'] += 1
                        if seq % 30 == 0:
                            await ws.send_json({'type':'ack','seq':seq,'server_ms':elapsed})
                        continue
                    data=json.loads(msg.data)
                    if not isinstance(data,dict): raise ValueError('Expected object')
                    if data.get('type')=='ping':
                        await ws.send_json({'type':'pong','time':data.get('time')})
                    elif data.get('type')=='select':
                        number = data.get('slot')
                        if type(number) is not int or not 1 <= number <= len(slots):
                            await ws.send_json({'type':'error','code':'invalid_slot','message':'Invalid application slot.'})
                            continue
                        target = slots[number-1]
                        if target['ws'] is not None and target['ws'] is not ws:
                            await ws.send_json({'type':'error','code':'slot_busy','message':'Application slot is already connected.'})
                            continue
                        if target is not state:
                            # No awaits until ownership has moved completely.
                            current_pad.reset()
                            state['armed'] = False
                            state['ws'] = None
                            target['ws'] = ws
                            state = target
                            current_pad = state['pad']
                            state['last'] = time.monotonic()
                        await ws.send_json({'type':'ready','slot':number,'mode':current_pad.mode,'message':current_pad.error, **roster()})
                        await broadcast()
                    elif data.get('type')=='state':
                        value=validate_state(data)
                        current_pad.apply(value)
                        state['last']=time.monotonic()
                        state['armed'] = True
                        state['count']+=1
                except (ValueError,TypeError):
                    await ws.close(code=1008,message=b'Invalid input')
                    break
        finally:
            current_pad.reset()
            state['armed'] = False
            state['ws']=None
            await broadcast()
        return ws
    async def lifecycle(app):
        async def watchdog():
            while True:
                await asyncio.sleep(.1)
                for state in slots:
                    if state['ws'] is not None and state['armed'] and time.monotonic()-state['last']>.5:
                        state['pad'].reset()
                        state['armed'] = False
        task=asyncio.create_task(watchdog())
        yield
        task.cancel()
        try: await task
        except asyncio.CancelledError: pass
        for state in slots:
            if state['ws'] is not None: await state['ws'].close(code=1001)
            state['pad'].reset()
    async def shutdown(app):
        clients = [s['ws'] for s in slots if s['ws'] is not None]
        for state in slots:
            state['pad'].reset()
            state['armed'] = False
        if clients:
            await asyncio.gather(*(ws.close(code=1001) for ws in clients), return_exceptions=True)

    app.on_shutdown.append(shutdown)
    app.cleanup_ctx.append(lifecycle)
    app.router.add_get('/',index)
    app.router.add_get('/host',host)
    app.router.add_get('/api/status',status)
    app.router.add_get('/api/qr',qr)
    app.router.add_get('/ws',ws_handler)
    app.router.add_static('/static',ROOT/'static')
    return app

if __name__=='__main__':
    parser=argparse.ArgumentParser(description='Pocket Pad desktop server')
    parser.add_argument('--port',type=int,default=8765)
    parser.add_argument('--https-port',type=int,default=8766)
    parser.add_argument('--diagnostic',action='store_true')
    parser.add_argument('--controllers', type=int, choices=range(1,5), default=4,
                        help='Application slots (not Windows XInput indices)')
    args=parser.parse_args()
    def make_pad():
        if not args.diagnostic:
            try: return XboxPad()
            except Exception as exc:
                print(f'XInput unavailable: {exc}\nRunning diagnostic mode for this slot.',flush=True)
        return DiagnosticPad()
    pads = [make_pad() for _ in range(args.controllers)]
    token = secrets.token_urlsafe(24)
    app = create_app(pads, token, args.port, https_port=args.https_port)
    
    async def run_dual_server():
        runner = web.AppRunner(app, access_log=None)
        await runner.setup()
        site_http = web.TCPSite(runner, '0.0.0.0', args.port)
        await site_http.start()
        
        https_ok = False
        try:
            from ssl_helper import get_or_create_ssl_context
            ssl_ctx, _, _ = get_or_create_ssl_context(ROOT / '.ssl', lan_ip())
            site_https = web.TCPSite(runner, '0.0.0.0', args.https_port, ssl_context=ssl_ctx)
            await site_https.start()
            https_ok = True
        except Exception as e:
            print(f'HTTPS disabled: {e}', flush=True)
            
        print(f'Desktop dashboard: http://localhost:{args.port}/host\nHTTP Server: http://{lan_ip()}:{args.port}\nHTTPS (Gyro): {"https://" + lan_ip() + ":" + str(args.https_port) if https_ok else "Disabled"}\nApplication slots: {len(pads)}\nModes: {", ".join(p.mode for p in pads)}', flush=True)
        
        while True:
            await asyncio.sleep(3600)
            
    try:
        asyncio.run(run_dual_server())
    except (KeyboardInterrupt, SystemExit):
        pass
