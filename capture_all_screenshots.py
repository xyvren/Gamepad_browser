"""Capture high-resolution screenshots of the Web Gamepad and Windows App."""
import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from PIL import ImageGrab
import ctypes
from ctypes import wintypes
from playwright.sync_api import sync_playwright

BASE_DIR = Path(__file__).resolve().parent
SHOTS_DIR = BASE_DIR / "screenshots"
SHOTS_DIR.mkdir(exist_ok=True)

URL_STATUS = "http://127.0.0.1:8765/api/status"

def is_server_ready():
    try:
        with urllib.request.urlopen(URL_STATUS, timeout=1) as r:
            return r.status == 200
    except Exception:
        return False

def get_token():
    with urllib.request.urlopen(URL_STATUS, timeout=2) as r:
        data = json.loads(r.read().decode())
        return data["url"].split("#token=")[1]

def main():
    server_proc = None
    if not is_server_ready():
        print("[*] Starting server for screenshot capture...")
        server_proc = subprocess.Popen([sys.executable, str(BASE_DIR / "server.py")])
        for _ in range(30):
            if is_server_ready():
                break
            time.sleep(0.2)
        else:
            raise RuntimeError("Failed to start server")

    token = get_token()
    print(f"[*] Server ready. Token: {token[:6]}...")

    with sync_playwright() as p:
        browser = p.chromium.launch()

        # 1. Mobile Menu Viewport (Portrait / Phone)
        print("[*] Capturing mobile menu...")
        page_mobile = browser.new_page(
            viewport={"width": 412, "height": 890},
            device_scale_factor=2,
            has_touch=True,
            is_mobile=True
        )
        page_mobile.goto(f"http://127.0.0.1:8765/#token={token}")
        page_mobile.wait_for_function("['online','diagnostic'].includes(document.body.dataset.connection)")
        page_mobile.wait_for_timeout(600)
        page_mobile.screenshot(path=str(SHOTS_DIR / "mobile-menu.png"))

        # 2. Mobile Layout Editor (Landscape)
        print("[*] Capturing layout & resize editor...")
        page_landscape = browser.new_page(
            viewport={"width": 890, "height": 412},
            device_scale_factor=2,
            has_touch=True,
            is_mobile=True
        )
        page_landscape.goto(f"http://127.0.0.1:8765/#token={token}")
        page_landscape.wait_for_function("['online','diagnostic'].includes(document.body.dataset.connection)")
        page_landscape.locator("#edit-layout").click()
        page_landscape.wait_for_selector("#edit-tools", state="visible")
        # Select cross button and enlarge
        page_landscape.locator('[data-button="cross"]').click()
        page_landscape.locator("#scale-up").click()
        page_landscape.locator("#scale-up").click()
        page_landscape.wait_for_timeout(400)
        page_landscape.screenshot(path=str(SHOTS_DIR / "layout-editor.png"))

        # 3. Pure Fullscreen Gamepad (Landscape)
        print("[*] Capturing pure fullscreen gamepad...")
        page_pad = browser.new_page(
            viewport={"width": 915, "height": 412},
            device_scale_factor=2,
            has_touch=True,
            is_mobile=True
        )
        page_pad.goto(f"http://127.0.0.1:8765/#token={token}")
        page_pad.wait_for_function("['online','diagnostic'].includes(document.body.dataset.connection)")
        # Click Run Gamepad
        page_pad.locator("#run-gamepad").click()
        page_pad.wait_for_selector(".pad", state="visible")
        page_pad.wait_for_timeout(500)
        page_pad.screenshot(path=str(SHOTS_DIR / "mobile-gamepad.png"))

        # 3b. Gyro Steering Wheel Mode (Landscape)
        print("[*] Capturing gyro steering wheel mode...")
        page_gyro = browser.new_page(
            viewport={"width": 915, "height": 412},
            device_scale_factor=2,
            has_touch=True,
            is_mobile=True
        )
        page_gyro.goto(f"http://127.0.0.1:8765/#token={token}")
        page_gyro.wait_for_function("['online','diagnostic'].includes(document.body.dataset.connection)")
        # Toggle gyro
        page_gyro.locator("#quick-toggle-gyro").click()
        page_gyro.wait_for_timeout(200)
        # Click Run Gamepad
        page_gyro.locator("#run-gamepad").click()
        page_gyro.wait_for_selector("#gyro-overlay", state="visible")
        page_gyro.evaluate("""() => {
            const event = new Event('deviceorientation');
            event.beta = 24;
            event.gamma = 0;
            window.dispatchEvent(event);
            document.getElementById('gyro-wheel').style.transform = 'rotate(24deg)';
            document.getElementById('gyro-angle-display').textContent = '+24°';
        }""")
        page_gyro.wait_for_timeout(500)
        page_gyro.screenshot(path=str(SHOTS_DIR / "gyro-steering-mode.png"))

        # 4. Desktop Web Dashboard
        print("[*] Capturing desktop web dashboard...")
        page_host = browser.new_page(
            viewport={"width": 1280, "height": 820},
            device_scale_factor=1.5
        )
        page_host.goto("http://127.0.0.1:8765/host")
        page_host.wait_for_function("document.querySelector('.qr') && document.querySelector('.qr').complete && document.querySelector('.qr').naturalWidth > 0")
        page_host.wait_for_timeout(600)
        page_host.screenshot(path=str(SHOTS_DIR / "desktop-web-dashboard.png"))

        browser.close()

    # 5. Capture Windows Native App GUI (Gamepad.exe / app_gui.py)
    print("[*] Capturing Windows native app...")
    gui_proc = subprocess.Popen([sys.executable, str(BASE_DIR / "app_gui.py")])
    time.sleep(2.0)

    try:
        # Find window by title
        user32 = ctypes.windll.user32
        hwnd = user32.FindWindowW(None, "Pocket Pad - Virtual Gamepad Desktop")
        if hwnd:
            user32.SetForegroundWindow(hwnd)
            time.sleep(0.5)
            rect = wintypes.RECT()
            user32.GetWindowRect(hwnd, ctypes.byref(rect))
            bbox = (rect.left, rect.top, rect.right, rect.bottom)
            img = ImageGrab.grab(bbox=bbox)
            img.save(str(SHOTS_DIR / "windows-desktop-app.png"))
            print(f"[OK] Saved windows-desktop-app.png ({img.size})")
        else:
            print("[!] Warning: Could not find Windows App window handle.")
    finally:
        gui_proc.terminate()
        try:
            gui_proc.wait(timeout=3)
        except Exception:
            gui_proc.kill()

    if server_proc:
        server_proc.terminate()
        try:
            server_proc.wait(timeout=3)
        except Exception:
            server_proc.kill()

    print("\n[SUCCESS] All screenshots captured in screenshots/ directory:")
    for f in SHOTS_DIR.glob("*.png"):
        print(f" - {f.name} ({f.stat().st_size:,} bytes)")

if __name__ == "__main__":
    main()
