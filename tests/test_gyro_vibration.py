"""Test suite for rumble vibration and dual HTTP/HTTPS support."""
import asyncio
import json
import pytest
from pathlib import Path
from server import DiagnosticPad, XboxPad, create_app, lan_ip
from aiohttp import web, ClientSession

@pytest.mark.asyncio
async def test_diagnostic_pad_rumble_callback():
    pad = DiagnosticPad()
    received = []
    pad.set_rumble_callback(lambda large, small: received.append((large, small)))
    pad.trigger_rumble(200, 100)
    assert received == [(200, 100)]

@pytest.mark.asyncio
async def test_websocket_receives_rumble_notification():
    pad = DiagnosticPad()
    token = "test_rumble_token"
    app = create_app([pad], token, 8765)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 8988)
    await site.start()
    
    try:
        async with ClientSession() as session:
            ws = await session.ws_connect(f"http://127.0.0.1:8988/ws?token={token}&slot=1")
            ready = await ws.receive_json()
            assert ready["type"] == "ready"
            
            # Allow roster broadcast to pass if present
            # Trigger rumble on pad
            pad.trigger_rumble(255, 128)
            
            # Wait for rumble message on websocket
            rumble_msg = None
            for _ in range(5):
                msg = await asyncio.wait_for(ws.receive_json(), timeout=2.0)
                if msg.get("type") == "rumble":
                    rumble_msg = msg
                    break
            
            assert rumble_msg is not None
            assert rumble_msg["type"] == "rumble"
            assert rumble_msg["large"] == 255
            assert rumble_msg["small"] == 128
            
            await ws.close()
    finally:
        await runner.cleanup()

@pytest.mark.asyncio
async def test_status_endpoint_returns_https_url():
    pad = DiagnosticPad()
    token = "test_status_token"
    app = create_app([pad], token, 8765, https_port=8766)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 8989)
    await site.start()
    
    try:
        async with ClientSession() as session:
            async with session.get("http://127.0.0.1:8989/api/status") as resp:
                assert resp.status == 200
                data = await resp.json()
                assert "url" in data
                assert "https_url" in data
                assert ":8766/" in data["https_url"]
                assert data["https_url"].startswith("https://")
    finally:
        await runner.cleanup()
