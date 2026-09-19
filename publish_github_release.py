"""Publish GitHub Release and upload binaries for xyvren/Gamepad_browser."""
import json
import os
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path

REPO = "xyvren/Gamepad_browser"
TAG = "v1.0.0"
TITLE = "Pocket Pad v1.0.0 — Virtual Gamepad for PC"

BODY = """# 🎮 Pocket Pad v1.0.0 — Initial Release

Turn your smartphone into a low-latency virtual Xbox 360 / XInput controller for PC games via local Wi-Fi!

No smartphone apps required — just scan the QR code displayed on your PC screen and your mobile browser instantly becomes a fullscreen touch controller.

---

### ✨ Features
- **Standalone Windows App (`Gamepad.exe`)**:
  - One-click native desktop app with embedded QR code.
  - No Python installation needed for end users (all batteries included).
  - Multi-slot monitor for up to 4 simultaneous players.
  - Quick actions for ViGEmBus driver setup and Windows Firewall.
- **Pure Fullscreen Mobile Gamepad**:
  - Clean, distraction-free touch surface without text or headers.
  - PlayStation / Xbox layout: D-Pad, Dual Analog Sticks, Action Buttons (× ○ □ △), L1/R1, L2/R2, L3/R3, Share, Options, and Home.
- **Customizable Button Scaling & Layout**:
  - Scale individual buttons from 60% up to 220% (`＋` / `－` controls).
  - Two-finger pinch-to-zoom support directly on touch surface.
  - Free drag-and-drop position editor with auto-save to phone storage.
- **Ultra-Low Latency Protocol (16-Byte Binary)**:
  - Raw binary ArrayBuffer stream over WebSocket with TCP_NODELAY.
  - Sub-millisecond response time (average 0.06 ms driver apply time).
- **Windows Installer (`Installer.exe`)**:
  - 1-click wizard to set up Desktop and Start Menu shortcuts, configure Windows Firewall, and check ViGEmBus drivers.

---

### 📥 Getting Started (No Python Required)
1. Download **`PocketPad-v1.0.0-Windows.zip`** below and extract it.
2. Run **`Installer.exe`** to set up Desktop shortcuts, driver, and firewall.
3. Double-click the **Pocket Pad** shortcut on your Desktop (or run `Gamepad.exe`).
4. Scan the QR code using your phone camera (connect to the same Wi-Fi).
5. Tap **Run Gamepad** and enjoy your games!

---

### 📦 Assets Included:
- **`PocketPad-v1.0.0-Windows.zip`**: Complete package with `Gamepad.exe`, `Installer.exe`, driver installer, shortcuts, and documentation.
- **`Gamepad.exe`**: Standalone portable application.
"""

def get_token():
    p = subprocess.run(
        ["git", "credential", "fill"],
        input="protocol=https\nhost=github.com\n",
        capture_output=True,
        text=True,
        check=True
    )
    for line in p.stdout.splitlines():
        if line.startswith("password="):
            return line.split("password=", 1)[1].strip()
    raise RuntimeError("GitHub token not found in git credentials")

def upload_asset(upload_url_template, token, file_path, content_type="application/octet-stream"):
    file_path = Path(file_path)
    # GitHub upload url format: https://uploads.github.com/repos/.../releases/.../assets{?name,label}
    base_url = upload_url_template.split("{")[0]
    filename = file_path.name
    url = f"{base_url}?name={urllib.parse.quote(filename)}"

    size = file_path.stat().st_size
    print(f"[*] Uploading {filename} ({size / (1024*1024):.2f} MB)...")

    with open(file_path, "rb") as f:
        data = f.read()

    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"Bearer {token}",
            "User-Agent": "PocketPad-Release-Script",
            "Content-Type": content_type,
            "Content-Length": str(len(data)),
            "Accept": "application/vnd.github.v3+json"
        },
        method="POST"
    )

    with urllib.request.urlopen(req) as resp:
        res = json.loads(resp.read().decode())
        print(f"    [OK] Uploaded {filename} -> Asset ID {res.get('id')}")

def main():
    token = get_token()
    print("[*] Retrieved GitHub credentials.")

    # 1. Create Release
    payload = {
        "tag_name": TAG,
        "target_commitish": "main",
        "name": TITLE,
        "body": BODY,
        "draft": False,
        "prerelease": False
    }

    req = urllib.request.Request(
        f"https://api.github.com/repos/{REPO}/releases",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "User-Agent": "PocketPad-Release-Script",
            "Content-Type": "application/json",
            "Accept": "application/vnd.github.v3+json"
        },
        method="POST"
    )

    print(f"[*] Creating GitHub Release for {TAG} on {REPO}...")
    try:
        with urllib.request.urlopen(req) as resp:
            release_data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        if "already_exists" in error_body:
            print("[*] Release already exists. Fetching existing release...")
            req_get = urllib.request.Request(
                f"https://api.github.com/repos/{REPO}/releases/tags/{TAG}",
                headers={
                    "Authorization": f"Bearer {token}",
                    "User-Agent": "PocketPad-Release-Script",
                    "Accept": "application/vnd.github.v3+json"
                }
            )
            with urllib.request.urlopen(req_get) as resp_get:
                release_data = json.loads(resp_get.read().decode())
        else:
            raise RuntimeError(f"HTTP {e.code}: {error_body}")

    release_html_url = release_data.get("html_url")
    upload_url = release_data.get("upload_url")
    print(f"[OK] Release ready: {release_html_url}")

    # 2. Upload Assets
    zip_path = Path("PocketPad-v1.0.0-Windows.zip")
    exe_path = Path("Gamepad.exe")

    if zip_path.exists():
        upload_asset(upload_url, token, zip_path, "application/zip")
    else:
        print("[!] Warning: PocketPad-v1.0.0-Windows.zip not found")

    if exe_path.exists():
        upload_asset(upload_url, token, exe_path, "application/vnd.microsoft.portable-executable")
    else:
        print("[!] Warning: Gamepad.exe not found")

    print(f"\n[SUCCESS] Release published successfully!\nURL: {release_html_url}")

if __name__ == "__main__":
    main()
