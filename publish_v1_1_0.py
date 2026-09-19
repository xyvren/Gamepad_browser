"""Publish GitHub Release v1.1.0 for xyvren/Gamepad_browser."""
import json
import os
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path

REPO = "xyvren/Gamepad_browser"
TAG = "v1.1.0"
TITLE = "Pocket Pad v1.1.0 — Kemudi Gyro Setir & Efek Getaran (Haptics & Rumble)"

BODY = """# 🎮 Pocket Pad v1.1.0 — Kemudi Gyro & Efek Getaran

Versi **v1.1.0** menghadirkan pembaruan besar: **Kemudi Setir berbasis Gyro / Sensor Gerak** untuk game balap mobil dan **Sistem Getaran Ganda (Dual Vibration)** yang menghubungkan efek getar game PC langsung ke smartphone Anda!

---

### ✨ Fitur Baru di v1.1.0
1. **Kemudi Setir Sensor Gyro (Motion Steering Wheel)**:
   - Putar HP ke kiri dan kanan layaknya setir mobil sungguhan untuk membelokkan mobil di game balap (Forza Horizon, Need for Speed, F1, Assetto Corsa, GTA).
   - Sensor `DeviceOrientation` dipetakan secara mulus dan presisi ke sumbu belok stik kiri XInput (**Left Stick X: -32768 s/d +32767**).
   - Pengaturan sensitivitas sudut belok maksimal (20° s/d 90°, default 45°) dan deadzone tengah.
   - Tombol kalibrasi cepat **🎯 Center** di layar untuk menetapkan posisi genggaman tangan saat ini sebagai titik lurus.
   - Jarum kemudi setir virtual dan indikator derajat belok digital di layar HP.
   - Dukungan server HTTPS otomatis (Port 8766) dengan sertifikat SSL lokal agar browser Chrome/Safari mengizinkan akses sensor gerak.

2. **Sistem Getaran Ganda (Dual Vibration & Haptics)**:
   - **Getaran Sentuhan Layar (Haptic Touch)**: Getaran halus (*tactile kick*) setiap kali jempol menekan tombol, trigger, atau kemudi di layar kaca HP.
   - **Getaran Game PC (Force Feedback Rumble)**: Menangkap data motor getar Xbox 360 (*Large Motor* & *Small Motor*) dari game PC secara real-time via driver ViGEmBus, dan meneruskannya ke ponsel via WebSocket sehingga HP ikut bergetar saat mobil menabrak pembatas jalan, jalanan berbatu, tabrakan, tembakan, atau ledakan.

3. **Aplikasi Windows Native (`Gamepad.exe`) Dual Mode**:
   - Menjalankan server HTTP (8765) dan HTTPS (8766) secara bersamaan.
   - Tombol toggle mode di jendela desktop: beralih antara **Standar (HTTP)** dan **Gyro Setir (HTTPS)** yang langsung memperbarui QR code di layar PC.

---

### 📥 Cara Memulai (Tanpa Perlu Install Python)
1. Unduh **`PocketPad-v1.1.0-Windows.zip`** di bawah dan ekstrak.
2. Jalankan **`Installer.exe`** untuk membuat shortcut Desktop dan memastikan driver aktif.
3. Buka **Pocket Pad** di Desktop, pilih mode di aplikasi PC, dan scan QR code menggunakan kamera HP.
4. Nikmati sensasi mengemudi setir gyro dan getaran game langsung di tangan Anda!
"""

def get_github_token():
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        return token
    try:
        proc = subprocess.Popen(
            ["git", "credential", "fill"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        out, _ = proc.communicate(input="protocol=https\nhost=github.com\n\n")
        for line in out.splitlines():
            if line.startswith("password="):
                return line.split("=", 1)[1].strip()
    except Exception as e:
        print(f"[!] Error reading git credentials: {e}")
    return None

def tag_and_push():
    print(f"[*] Creating git tag {TAG}...")
    subprocess.run(["git", "tag", "-a", TAG, "-m", f"Release {TAG}"], check=False)
    print(f"[*] Pushing tag {TAG} to origin...")
    res = subprocess.run(["git", "push", "origin", TAG], capture_output=True, text=True)
    print(res.stdout or res.stderr)

def create_release(token):
    url = f"https://api.github.com/repos/{REPO}/releases"
    payload = {
        "tag_name": TAG,
        "target_commitish": "main",
        "name": TITLE,
        "body": BODY,
        "draft": False,
        "prerelease": False
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "User-Agent": "PocketPad-Release-Bot"
        },
        method="POST"
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        err_body = e.read().decode()
        if "already_exists" in err_body:
            print("[!] Release already exists, fetching existing release...")
            get_req = urllib.request.Request(
                f"https://api.github.com/repos/{REPO}/releases/tags/{TAG}",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.github+json",
                    "User-Agent": "PocketPad-Release-Bot"
                }
            )
            with urllib.request.urlopen(get_req) as r:
                return json.loads(r.read().decode())
        print(f"[!] HTTP Error {e.code}: {err_body}")
        raise

def upload_asset(token, upload_url_template, file_path):
    upload_url = upload_url_template.split("{")[0]
    filename = Path(file_path).name
    url = f"{upload_url}?name={urllib.parse.quote(filename)}"
    print(f"[*] Uploading {filename} ({os.path.getsize(file_path):,} bytes)...")
    
    with open(file_path, "rb") as f:
        data = f.read()
        
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/octet-stream",
            "User-Agent": "PocketPad-Release-Bot"
        },
        method="POST"
    )
    with urllib.request.urlopen(req) as resp:
        res = json.loads(resp.read().decode())
        print(f"[OK] Uploaded {filename} -> {res.get('browser_download_url')}")

def main():
    token = get_github_token()
    if not token:
        print("[!] GitHub token not found.")
        sys.exit(1)
        
    tag_and_push()
    rel = create_release(token)
    print(f"[OK] Release created: {rel.get('html_url')}")
    
    upload_url = rel.get("upload_url")
    if not upload_url:
        print("[!] No upload_url returned.")
        sys.exit(1)
        
    assets = [
        "PocketPad-v1.1.0-Windows.zip",
        "Gamepad.exe",
        "Installer.exe"
    ]
    for asset in assets:
        if os.path.exists(asset):
            try:
                upload_asset(token, upload_url, asset)
            except Exception as e:
                print(f"[!] Upload failed for {asset}: {e}")

if __name__ == "__main__":
    main()
