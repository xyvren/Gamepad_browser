"""Measure localhost transport -> driver apply -> ACK, not phone Wi-Fi latency."""
import asyncio
import json
import math
import statistics
import struct
import time
from pathlib import Path
from urllib.parse import parse_qs,urlparse
from aiohttp import ClientSession

async def run():
    async with ClientSession() as session:
        async with session.get('http://127.0.0.1:8765/api/status') as r:
            status=await r.json()
        token=parse_qs(urlparse(status['url']).fragment)['token'][0]
        async with session.ws_connect('http://127.0.0.1:8765/ws',params={'token':token},compress=0) as ws:
            ready=await ws.receive_json()
            assert ready['type']=='ready' and ready['mode']=='xinput',ready
            samples=[];processing=[]
            for i in range(220):
                seq=i*30
                packet=struct.pack('<HhhhhBBI',1 if i%2 else 0,0,0,0,0,0,0,seq)
                start=time.perf_counter_ns()
                await ws.send_bytes(packet)
                while True:
                    ack=await ws.receive_json(timeout=3)
                    if ack.get('type')=='ack' and ack.get('seq')==seq:break
                elapsed=(time.perf_counter_ns()-start)/1e6
                if i>=20:samples.append(elapsed);processing.append(ack['server_ms'])
            await ws.send_bytes(struct.pack('<HhhhhBBI',0,0,0,0,0,0,0,999999))
            def stats(values):
                values=sorted(values)
                return {'median_ms':round(statistics.median(values),3),'p95_ms':round(values[math.ceil(len(values)*.95)-1],3),'max_ms':round(max(values),3)}
            result={'scope':'localhost WebSocket send -> XInput apply -> ACK; NOT phone Wi-Fi, display latency, or game-frame latency','samples':len(samples),'packet_bytes':16,'input_ack_rtt':stats(samples),'server_apply':stats(processing)}
            Path('artifacts').mkdir(exist_ok=True)
            Path('artifacts/latency.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
            print(json.dumps(result,indent=2))
if __name__=='__main__':asyncio.run(run())
