"""Pocket Pad - Native Windows GUI Installer & Shortcut Creator."""
import os
import shutil
import subprocess
import sys
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path

BUNDLE_DIR = Path(getattr(sys, '_MEIPASS', Path(__file__).parent))

class InstallerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Pocket Pad - Installer")
        self.root.geometry("520x460")
        self.root.resizable(False, False)
        self.root.configure(bg="#121518")

        icon_path = BUNDLE_DIR / "icon.ico"
        if icon_path.exists():
            try:
                self.root.iconbitmap(str(icon_path))
            except Exception:
                pass

        self._build_ui()

    def _build_ui(self):
        # Header
        header = tk.Frame(self.root, bg="#1a1f24", height=64)
        header.pack(fill="x", side="top")

        lbl_title = tk.Label(
            header, text="POCKET PAD SETUP", font=("Segoe UI", 15, "bold"),
            fg="#d4f582", bg="#1a1f24"
        )
        lbl_title.pack(anchor="w", padx=20, pady=(12, 2))

        lbl_sub = tk.Label(
            header, text="Instalasi Gamepad Virtual Windows & Pembuat Shortcut",
            font=("Segoe UI", 9), fg="#8c98a4", bg="#1a1f24"
        )
        lbl_sub.pack(anchor="w", padx=20, pady=(0, 10))

        # Body
        body = tk.Frame(self.root, bg="#121518")
        body.pack(fill="both", expand=True, padx=24, pady=16)

        lbl_desc = tk.Label(
            body,
            text="Pilih opsi instalasi di bawah ini untuk menyiapkan Pocket Pad\n"
                 "agar siap digunakan untuk bermain game.",
            font=("Segoe UI", 9), fg="#cfd7de", bg="#121518", justify="left"
        )
        lbl_desc.pack(anchor="w", pady=(0, 14))

        # Options frame
        opts = tk.Frame(body, bg="#171c21", highlightbackground="#252c33", highlightthickness=1)
        opts.pack(fill="x", pady=6)

        self.cb_desktop = tk.BooleanVar(value=True)
        self.cb_startmenu = tk.BooleanVar(value=True)
        self.cb_firewall = tk.BooleanVar(value=True)
        self.cb_driver = tk.BooleanVar(value=True)

        self._add_checkbox(opts, "Buat Shortcut di Desktop", self.cb_desktop)
        self._add_checkbox(opts, "Buat Shortcut di Start Menu", self.cb_startmenu)
        self._add_checkbox(opts, "Buka Port Firewall Wi-Fi (Port TCP 8765)", self.cb_firewall)
        self._add_checkbox(opts, "Periksa & Pasang Driver ViGEmBus (XInput)", self.cb_driver)

        # Log box
        self.log_box = tk.Text(
            body, height=6, bg="#0d0f12", fg="#8e9ca8",
            font=("Consolas", 8), relief="flat", padx=8, pady=6
        )
        self.log_box.pack(fill="x", pady=12)
        self.log_box.insert("end", "Siap untuk instalasi.\n")
        self.log_box.configure(state="disabled")

        # Bottom buttons
        footer = tk.Frame(self.root, bg="#121518")
        footer.pack(fill="x", side="bottom", padx=24, pady=(0, 18))

        self.btn_install = tk.Button(
            footer, text="Pasang Sekarang", font=("Segoe UI", 10, "bold"),
            bg="#d4f582", fg="#12160d", activebackground="#e2fca0",
            activeforeground="#12160d", relief="flat", cursor="hand2",
            padx=16, pady=6, command=self.do_install
        )
        self.btn_install.pack(side="right")

        btn_cancel = tk.Button(
            footer, text="Tutup", font=("Segoe UI", 9),
            bg="#20262b", fg="#a0adb7", activebackground="#293138",
            activeforeground="#ffffff", relief="flat", cursor="hand2",
            padx=14, pady=6, command=self.root.destroy
        )
        btn_cancel.pack(side="right", padx=(0, 10))

    def _add_checkbox(self, parent, text, var):
        f = tk.Frame(parent, bg="#171c21")
        f.pack(fill="x", padx=14, pady=5)
        cb = tk.Checkbutton(
            f, text=text, variable=var, font=("Segoe UI", 9),
            fg="#e1e7eb", bg="#171c21", selectcolor="#252d35",
            activebackground="#171c21", activeforeground="#d4f582",
            cursor="hand2"
        )
        cb.pack(side="left")

    def log(self, text):
        self.log_box.configure(state="normal")
        self.log_box.insert("end", text + "\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")
        self.root.update_idletasks()

    def do_install(self):
        self.btn_install.configure(state="disabled")
        current_dir = Path(__file__).resolve().parent

        # 1. Check Driver
        if self.cb_driver.get():
            self.log("[*] Memeriksa driver ViGEmBus...")
            driver_sys = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "drivers" / "ViGEmBus.sys"
            if driver_sys.exists():
                self.log("    [OK] Driver ViGEmBus sudah terpasang.")
            else:
                installer = current_dir / "installers" / "ViGEmBus_1.22.0_x64_x86_arm64.exe"
                if installer.exists():
                    self.log("    [*] Menjalankan installer resmi ViGEmBus...")
                    try:
                        subprocess.run([str(installer)], check=False)
                        self.log("    [OK] Installer selesai dijalankan.")
                    except Exception as e:
                        self.log(f"    [!] Gagal menjalankan installer: {e}")
                else:
                    self.log("    [!] Installer ViGEmBus tidak ditemukan.")

        # 2. Firewall
        if self.cb_firewall.get():
            self.log("[*] Mengatur Windows Firewall (Port TCP 8765 & 8766)...")
            ps_script = current_dir / "enable-firewall.ps1"
            if ps_script.exists():
                try:
                    cmd = f'powershell.exe -Command "Start-Process powershell -Verb RunAs -Wait -ArgumentList \'-NoProfile -ExecutionPolicy Bypass -File \"\"{str(ps_script)}\"\"\'"'
                    subprocess.run(cmd, shell=True)
                    self.log("    [OK] Firewall rule diproses.")
                except Exception as e:
                    self.log(f"    [!] Gagal mengatur firewall: {e}")

        # 3. Shortcuts
        if self.cb_desktop.get() or self.cb_startmenu.get():
            self.log("[*] Membuat shortcut...")
            ps_script = current_dir / "create_shortcut.ps1"
            if ps_script.exists():
                try:
                    cmd = f'powershell.exe -NoProfile -ExecutionPolicy Bypass -File "{str(ps_script)}" -TargetDir "{str(current_dir)}"'
                    res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                    if res.stdout:
                        for line in res.stdout.strip().splitlines():
                            self.log(f"    {line}")
                except Exception as e:
                    self.log(f"    [!] Gagal membuat shortcut: {e}")

        self.log("\n[SELESAI] Instalasi berhasil!")
        self.btn_install.configure(state="normal", text="Selesai", command=self._finish)

    def _finish(self):
        current_dir = Path(__file__).resolve().parent
        gamepad_exe = current_dir / "Gamepad.exe"
        if gamepad_exe.exists():
            if messagebox.askyesno("Pocket Pad", "Instalasi selesai!\n\nJalankan Pocket Pad sekarang?"):
                subprocess.Popen([str(gamepad_exe)], cwd=str(current_dir))
        self.root.destroy()

def main():
    root = tk.Tk()
    app = InstallerApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
