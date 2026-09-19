"""Pocket Pad - Native Windows GUI Application with Embedded QR Code & Server."""
import asyncio
import io
import os
import secrets
import socket
import subprocess
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox
import urllib.request
import webbrowser
from pathlib import Path
from PIL import Image, ImageTk
import qrcode

# Support PyInstaller frozen bundle path
BUNDLE_DIR = Path(getattr(sys, '_MEIPASS', Path(__file__).parent))
sys.path.insert(0, str(BUNDLE_DIR))

from server import XboxPad, DiagnosticPad, create_app, lan_ip
from aiohttp import web

class GamepadApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Pocket Pad - Virtual Gamepad Desktop")
        self.root.geometry("820x600")
        self.root.minsize(760, 560)
        self.root.configure(bg="#111417")

        # Set window icon if exists
        icon_path = BUNDLE_DIR / "icon.ico"
        if icon_path.exists():
            try:
                self.root.iconbitmap(str(icon_path))
            except Exception:
                pass

        self.port = 8765
        self.https_port = 8766
        self.capacity = 4
        self.pads = []
        self.token = secrets.token_urlsafe(24)
        self.server_thread = None
        self.loop = None
        self.runner = None
        self.site = None
        self.https_site = None
        self.running = True
        self.qr_photo = None
        self.url = f"http://{lan_ip()}:{self.port}/#token={self.token}"

        self._init_pads()
        self._build_ui()
        self._start_server_thread()
        self._start_polling()

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def _init_pads(self):
        self.pads = []
        for i in range(self.capacity):
            try:
                p = XboxPad()
            except Exception as e:
                p = DiagnosticPad()
            self.pads.append(p)

    def _start_server_thread(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        in_use = s.connect_ex(('127.0.0.1', self.port)) == 0
        s.close()
        
        if in_use:
            try:
                req = urllib.request.Request(f"http://127.0.0.1:{self.port}/api/status")
                with urllib.request.urlopen(req, timeout=1) as r:
                    data = json.loads(r.read().decode())
                    if "url" in data and "#token=" in data["url"]:
                        self.url = data["url"]
                        self.token = data["url"].split("#token=")[1]
                        self.url_var.set(self.url)
                        self._update_qr_image()
                        return
            except Exception:
                pass

        def run_loop():
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            app = create_app(self.pads, self.token, self.port, capacity=self.capacity, https_port=self.https_port)
            self.runner = web.AppRunner(app, access_log=None)
            self.loop.run_until_complete(self.runner.setup())
            self.site = web.TCPSite(self.runner, "0.0.0.0", self.port)
            self.loop.run_until_complete(self.site.start())

            try:
                from ssl_helper import get_or_create_ssl_context
                ssl_ctx, _, _ = get_or_create_ssl_context(BUNDLE_DIR / ".ssl", lan_ip())
                self.https_site = web.TCPSite(self.runner, "0.0.0.0", self.https_port, ssl_context=ssl_ctx)
                self.loop.run_until_complete(self.https_site.start())
            except Exception as e:
                print(f"HTTPS site skipped in GUI: {e}")

            self.loop.run_forever()

        self.server_thread = threading.Thread(target=run_loop, daemon=True)
        self.server_thread.start()

    def _build_ui(self):
        # Header banner
        header = tk.Frame(self.root, bg="#181c20", height=64)
        header.pack(fill="x", side="top")

        title_box = tk.Frame(header, bg="#181c20")
        title_box.pack(side="left", padx=20, pady=12)

        lbl_title = tk.Label(
            title_box, text="POCKET PAD", font=("Segoe UI", 16, "bold"),
            fg="#d4f582", bg="#181c20"
        )
        lbl_title.pack(side="left")

        lbl_sub = tk.Label(
            title_box, text="  Virtual Gamepad for Windows",
            font=("Segoe UI", 10), fg="#7f8b95", bg="#181c20"
        )
        lbl_sub.pack(side="left", pady=(4, 0))

        # Status badge on right
        self.mode_badge = tk.Label(
            header, text="● XInput Aktif", font=("Segoe UI", 10, "bold"),
            fg="#d4f582" if any(p.mode == "xinput" for p in self.pads) else "#f5a623",
            bg="#21272c", padx=12, pady=4, relief="flat"
        )
        self.mode_badge.pack(side="right", padx=20, pady=16)

        # Main container with 2 columns
        main = tk.Frame(self.root, bg="#111417")
        main.pack(fill="both", expand=True, padx=20, pady=15)

        # Left Column: QR Code & Connection Link
        left = tk.Frame(main, bg="#181c20", width=340, highlightbackground="#272e34", highlightthickness=1)
        left.pack(side="left", fill="both", padx=(0, 10))
        left.pack_propagate(False)

        lbl_qr_title = tk.Label(
            left, text="Scan Menggunakan HP", font=("Segoe UI", 12, "bold"),
            fg="#e3e8ec", bg="#181c20"
        )
        lbl_qr_title.pack(pady=(16, 4))

        lbl_qr_sub = tk.Label(
            left, text="Buka kamera / QR scanner di HP yang terhubung\nke Wi-Fi yang sama untuk langsung terhubung.",
            font=("Segoe UI", 8), fg="#7f8b95", bg="#181c20", justify="center"
        )
        lbl_qr_sub.pack(pady=(0, 10))

        # Mode selector (Standard HTTP vs Gyro Steering HTTPS)
        mode_frame = tk.Frame(left, bg="#181c20")
        mode_frame.pack(fill="x", padx=18, pady=(0, 6))

        self.proto_var = tk.StringVar(value="http")

        rb_http = tk.Radiobutton(
            mode_frame, text="Standar (HTTP)", variable=self.proto_var, value="http",
            command=self._on_proto_change, font=("Segoe UI", 8, "bold"),
            fg="#d4f582", bg="#181c20", selectcolor="#101315", activebackground="#181c20", activeforeground="#d4f582"
        )
        rb_http.pack(side="left", padx=(0, 8))

        rb_https = tk.Radiobutton(
            mode_frame, text="Gyro Setir (HTTPS)", variable=self.proto_var, value="https",
            command=self._on_proto_change, font=("Segoe UI", 8, "bold"),
            fg="#d4f582", bg="#181c20", selectcolor="#101315", activebackground="#181c20", activeforeground="#d4f582"
        )
        rb_https.pack(side="left")

        # QR Code Display
        self.qr_label = tk.Label(left, bg="#181c20")
        self.qr_label.pack(pady=4)
        self._update_qr_image()

        # URL Box & Copy Button
        url_frame = tk.Frame(left, bg="#181c20")
        url_frame.pack(fill="x", padx=18, pady=(10, 5))

        self.url_var = tk.StringVar(value=self.url)
        url_entry = tk.Entry(
            url_frame, textvariable=self.url_var, font=("Segoe UI", 8),
            fg="#bac4cb", bg="#101315", relief="flat", insertbackground="white"
        )
        url_entry.pack(side="left", fill="x", expand=True, ipady=4, padx=(0, 5))

        btn_copy = tk.Button(
            url_frame, text="Salin", font=("Segoe UI", 8, "bold"),
            bg="#262e34", fg="#d4f582", relief="flat", cursor="hand2",
            activebackground="#313b42", activeforeground="#d4f582",
            command=self._copy_url, padx=8, pady=2
        )
        btn_copy.pack(side="right")

        # Open Web Host button
        btn_web = tk.Button(
            left, text="🌐 Buka Dashboard Web", font=("Segoe UI", 9),
            bg="#232a30", fg="#c8d1d8", relief="flat", cursor="hand2",
            activebackground="#2c353c", activeforeground="#ffffff",
            command=self._open_web_host, pady=5
        )
        btn_web.pack(fill="x", padx=18, pady=(10, 16))

        # Right Column: Slots & Diagnostics
        right = tk.Frame(main, bg="#111417")
        right.pack(side="right", fill="both", expand=True, padx=(10, 0))

        # Slots title
        slots_header = tk.Frame(right, bg="#111417")
        slots_header.pack(fill="x", pady=(0, 8))

        tk.Label(
            slots_header, text="Slot Controller (Maksimal 4)", font=("Segoe UI", 12, "bold"),
            fg="#e3e8ec", bg="#111417"
        ).pack(side="left")

        self.lbl_connected_count = tk.Label(
            slots_header, text="0 / 4 Terhubung", font=("Segoe UI", 9, "bold"),
            fg="#7f8b95", bg="#111417"
        )
        self.lbl_connected_count.pack(side="right")

        # 4 Slot Cards
        self.slot_cards = []
        for i in range(1, self.capacity + 1):
            card = tk.Frame(right, bg="#181c20", highlightbackground="#272e34", highlightthickness=1, height=72)
            card.pack(fill="x", pady=4)
            card.pack_propagate(False)

            # Slot number badge
            num_badge = tk.Label(
                card, text=f"P{i}", font=("Segoe UI", 13, "bold"),
                fg="#bac4cb", bg="#22282e", width=4, relief="flat"
            )
            num_badge.pack(side="left", fill="y", padx=(0, 12))

            info_frame = tk.Frame(card, bg="#181c20")
            info_frame.pack(side="left", fill="y", pady=10)

            name_lbl = tk.Label(
                info_frame, text=f"Controller Slot {i}", font=("Segoe UI", 10, "bold"),
                fg="#e3e8ec", bg="#181c20"
            )
            name_lbl.pack(anchor="w")

            status_lbl = tk.Label(
                info_frame, text="Menunggu koneksi dari HP...", font=("Segoe UI", 8),
                fg="#6b7782", bg="#181c20"
            )
            status_lbl.pack(anchor="w")

            stat_box = tk.Frame(card, bg="#181c20")
            stat_box.pack(side="right", padx=16, pady=12)

            packets_lbl = tk.Label(
                stat_box, text="0 pkt", font=("Segoe UI", 9),
                fg="#54606b", bg="#181c20"
            )
            packets_lbl.pack(anchor="e")

            dot_lbl = tk.Label(
                stat_box, text="● Offline", font=("Segoe UI", 8, "bold"),
                fg="#54606b", bg="#181c20"
            )
            dot_lbl.pack(anchor="e")

            self.slot_cards.append({
                "frame": card,
                "num": num_badge,
                "name": name_lbl,
                "status": status_lbl,
                "packets": packets_lbl,
                "dot": dot_lbl
            })

        # Bottom Tools Frame
        tools = tk.Frame(right, bg="#111417")
        tools.pack(fill="x", side="bottom", pady=(10, 0))

        btn_driver = tk.Button(
            tools, text="⚙️ Install ViGEmBus", font=("Segoe UI", 8),
            bg="#1d2328", fg="#9aa5ae", relief="flat", cursor="hand2",
            command=self._install_driver, pady=5, padx=8
        )
        btn_driver.pack(side="left", padx=(0, 6))

        btn_firewall = tk.Button(
            tools, text="🛡️ Buka Port Firewall", font=("Segoe UI", 8),
            bg="#1d2328", fg="#9aa5ae", relief="flat", cursor="hand2",
            command=self._enable_firewall, pady=5, padx=8
        )
        btn_firewall.pack(side="left", padx=(0, 6))

        btn_refresh = tk.Button(
            tools, text="🔄 Reset Token", font=("Segoe UI", 8),
            bg="#1d2328", fg="#9aa5ae", relief="flat", cursor="hand2",
            command=self._regenerate_token, pady=5, padx=8
        )
        btn_refresh.pack(side="right")

    def _update_qr_image(self):
        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=6,
            border=2,
        )
        qr.add_data(self.url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="#101214", back_color="#ffffff").convert("RGB")
        img = img.resize((210, 210), Image.Resampling.NEAREST)
        self.qr_photo = ImageTk.PhotoImage(img)
        self.qr_label.configure(image=self.qr_photo)

    def _copy_url(self):
        self.root.clipboard_clear()
        self.root.clipboard_append(self.url)
        messagebox.showinfo("Tersalin", "URL pairing berhasil disalin ke clipboard!")

    def _open_web_host(self):
        webbrowser.open(f"http://127.0.0.1:{self.port}/host")

    def _install_driver(self):
        installer = BUNDLE_DIR / "installers" / "ViGEmBus_1.22.0_x64_x86_arm64.exe"
        if installer.exists():
            try:
                subprocess.Popen([str(installer)])
            except Exception as e:
                messagebox.showerror("Error", f"Gagal menjalankan installer:\n{e}")
        else:
            webbrowser.open("https://github.com/nefarius/ViGEmBus/releases/tag/v1.22.0")

    def _enable_firewall(self):
        ps_script = BUNDLE_DIR / "enable-firewall.ps1"
        if ps_script.exists():
            cmd = f'powershell.exe -Command "Start-Process powershell -Verb RunAs -ArgumentList \'-NoProfile -ExecutionPolicy Bypass -File \"\"{str(ps_script)}\"\"\'"'
            subprocess.run(cmd, shell=True)
            messagebox.showinfo("Firewall", "Rule firewall untuk port TCP 8765 & 8766 sedang diproses lewat PowerShell Administrator.")

    def _on_proto_change(self):
        proto = self.proto_var.get()
        p = self.https_port if proto == "https" else self.port
        self.url = f"{proto}://{lan_ip()}:{p}/#token={self.token}"
        self.url_var.set(self.url)
        self._update_qr_image()

    def _regenerate_token(self):
        self.token = secrets.token_urlsafe(24)
        proto = self.proto_var.get()
        p = self.https_port if proto == "https" else self.port
        self.url = f"{proto}://{lan_ip()}:{p}/#token={self.token}"
        self.url_var.set(self.url)
        self._update_qr_image()

    def _start_polling(self):
        def poll():
            if not self.running:
                return
            try:
                req = urllib.request.Request(f"http://127.0.0.1:{self.port}/api/status", headers={"User-Agent": "PocketPadGUI"})
                with urllib.request.urlopen(req, timeout=0.8) as r:
                    data = json.loads(r.read().decode())
                
                count = data.get("connected_count", 0)
                cap = data.get("capacity", 4)
                self.lbl_connected_count.config(
                    text=f"{count} / {cap} Terhubung",
                    fg="#d4f582" if count > 0 else "#7f8b95"
                )

                slots = data.get("slots", [])
                for i, s in enumerate(slots):
                    if i < len(self.slot_cards):
                        card = self.slot_cards[i]
                        conn = s.get("connected", False)
                        mode = s.get("mode", "diagnostic")
                        pkts = s.get("packets", 0)

                        if conn:
                            card["frame"].config(highlightbackground="#d4f582", highlightthickness=1)
                            card["num"].config(bg="#d4f582", fg="#12160d")
                            card["status"].config(text=f"Terhubung · Mode {mode.upper()}", fg="#d4f582")
                            card["dot"].config(text="● AKTIF", fg="#d4f582")
                            card["packets"].config(text=f"{pkts:,} pkt", fg="#ccd5dc")
                        else:
                            card["frame"].config(highlightbackground="#272e34", highlightthickness=1)
                            card["num"].config(bg="#22282e", fg="#bac4cb")
                            card["status"].config(text="Menunggu koneksi dari HP...", fg="#6b7782")
                            card["dot"].config(text="○ Standby", fg="#54606b")
                            card["packets"].config(text=f"{pkts:,} pkt" if pkts else "0 pkt", fg="#54606b")
            except Exception:
                pass

            if self.running:
                self.root.after(600, poll)

        self.root.after(800, poll)

    def on_close(self):
        self.running = False
        try:
            for p in self.pads:
                p.reset()
        except Exception:
            pass
        self.root.destroy()
        # Ensure clean process termination
        os._exit(0)

def main():
    root = tk.Tk()
    app = GamepadApp(root)
    root.mainloop()

if __name__ == "__main__":
    import json
    main()
