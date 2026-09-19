# Pocket Pad 🎮

**Pocket Pad** adalah aplikasi gamepad virtual web untuk smartphone yang terhubung langsung ke PC Windows via Wi-Fi lokal, mengemulasikan controller fisik **Xbox 360 / XInput** secara real-time dengan latensi ultra-rendah (sub-milidetik).

Cukup scan QR code dari layar monitor menggunakan HP, dan HP Anda seketika berubah menjadi gamepad nirkabel layar penuh tanpa perlu install aplikasi tambahan di ponsel.

---

## ✨ Fitur Utama

- **Tampilan Gamepad Fullscreen Murni**:
  - Saat bermain (*Run Gamepad*), layar HP 100% bersih hanya berisi tombol gamepad tanpa header, footer, teks status, atau tombol antarmuka yang mengganggu.
  - Tampilan controller bergaya PlayStation / Xbox (D-Pad, × ○ □ △, L1/R1, L2/R2, L3/R3, Dual Analog Stick, Share, Options, Home).
- **Menu Setup Interaktif di HP**:
  - **Slot Controller 1–4 (Multiplayer)**: Mendukung hingga 4 HP terhubung bersamaan ke 1 PC sebagai Pemain 1, 2, 3, dan 4.
  - **Indikator Koneksi & Slot**: Menampilkan slot stik aktif Anda (`Stik 01`) dan jumlah HP yang terhubung (`1 / 4 terhubung`).
  - **Status Latensi Real-Time**: Menampilkan PING RTT dan round-trip ACK input secara live.
- **Kustomisasi Posisi & Ukuran Tombol (Drag & Scale)**:
  - **Perbesar / Perkecil Per Tombol**: Ketuk tombol mana saja di mode edit, lalu atur ukurannya dengan tombol `＋` / `－` (skala 60% s/d 220%).
  - **Gesture 2 Jari (Pinch-to-Zoom)**: Cubit atau lebarkan dua jari langsung pada tombol/layar untuk memperbesar atau memperkecil secara fleksibel.
  - **Geser Bebas (Drag & Drop)**: Pindahkan posisi setiap tombol dan analog sesuai jangkauan jempol Anda.
  - **Slider Ukuran Global**: Tersedia slider untuk mengubah ukuran seluruh tombol atau seluruh analog stik sekaligus di menu pengaturan.
  - **Penyimpanan Otomatis**: Posisi dan ukuran tersimpan permanen di `localStorage` HP (tata letak *landscape* dan *portrait* tersimpan terpisah).
- **Remapping & Pengaturan Analog**:
  - Remap fungsi setiap tombol ke tombol controller mana pun.
  - Pengaturan *radial deadzone* analog agar bidikan/gerakan tidak *drifting*.
  - Opsi *Swap Sticks* untuk menukar analog kiri dan kanan (cocok untuk kidal).
- **Protokol Biner 16-Byte Ultra-Low Latency**:
  - Mengirim stream data biner mentah (*ArrayBuffer*) 16 byte per paket melalui WebSocket lokal.
  - Dilengkapi `TCP_NODELAY` dan kompresi nonaktif (*zero serialization delay* & *zero GC pause*).
  - Benchmark latensi input ke driver Windows rata-rata **0,06 ms** dengan RTT transmisi lokal **0,27 ms**.
- **Dashboard Desktop Host dengan QR Code**:
  - Deteksi otomatis IP Wi-Fi lokal PC.
  - Menampilkan QR code dinamis dengan token autentikasi sesi rahasia.
  - Monitor status dan aktivitas input 4 slot controller secara visual di monitor PC.
- **Watchdog & Auto-Neutral**:
  - Input otomatis dinetralkan jika koneksi terputus, HP diminimalkan, atau layar mati, mencegah tombol tersangkut (*stuck key*) di dalam game.

---

## 📁 Struktur File Lengkap Proyek

```text
controler/
├── .gitignore                   # Konfigurasi file yang diabaikan Git
├── LICENSE                      # Lisensi open-source MIT
├── README.md                    # Dokumentasi lengkap proyek
├── requirements.txt             # Dependensi runtime Python (aiohttp, qrcode, pillow, vgamepad)
├── requirements-dev.txt         # Dependensi testing (pytest, pytest-asyncio, playwright)
├── setup.bat                    # Script otomatis instalasi environment & dependensi
├── start.bat                    # Script satu-klik untuk menjalankan server & membuka dashboard
├── launch.py                    # Launcher otomatis server background & web host
├── server.py                    # Server HTTP & WebSocket biner (manajemen 4 slot XInput)
├── protocol.py                  # Definisi protokol tombol, validasi state, & normalisasi axis
├── enable-firewall.ps1          # Script PowerShell pembuka firewall port TCP 8765 LAN
├── installers/
│   └── ViGEmBus_1.22.0_...exe  # Installer resmi driver ViGEmBus Windows XInput
├── static/
│   ├── index.html               # Halaman web controller HP (Menu, Editor, Gamepad)
│   ├── app.js                   # Logika antarmuka HP, pointer events, drag & drop, touch scale
│   ├── input.js                 # Encoder paket biner 16-byte, remap buttons, analog processing
│   ├── controller.css           # Styling visual gamepad fullscreen & scaling CSS
│   ├── menu.css                 # Styling menu landing page HP & dialog settings
│   ├── host.html                # Dashboard desktop host untuk monitor 4 slot & QR code
│   ├── host.js                  # Logika dashboard host & polling status
│   └── style.css                # Styling dasar dashboard host
└── tests/
    ├── test_protocol.py         # Unit test validasi input & tombol
    ├── test_server.py           # Unit test server endpoint API & WebSocket handshake
    ├── test_backend_slots.py    # Unit test alokasi slot stik 1–4 & isolasi multi-client
    ├── test_launch.py           # Unit test launcher subprocess
    ├── test_surface.py          # Unit test aset statis web
    ├── input.test.cjs           # Unit test wire format biner 16-byte (Node.js)
    ├── verify_scaling.py        # Acceptance test Playwright: perbesar/perkecil tombol & persistensi
    ├── verify_menu.py           # Acceptance test Playwright: navigasi menu & pemilihan slot
    ├── verify_layout.py         # Acceptance test Playwright: editor posisi & boundaries
    ├── verify_live.py           # E2E test Playwright: integrasi browser touch ke driver XInput
    └── verify_latency.py        # Benchmark pengujian latensi pemrosesan input
```

---

## ⚙️ Persyaratan Sistem

1. **PC / Laptop (Host Server)**:
   - Sistem Operasi: **Windows 10 / 11 (64-bit)**.
   - Python: Versi **3.10 atau lebih baru** (atau [uv](https://docs.astral.sh/uv/)).
   - Driver Gamepad: **ViGEmBus 1.22.0** (installer resmi sudah disertakan di folder `installers/`).
2. **Smartphone (Client Controller)**:
   - Perangkat: Android atau iOS (iPhone / iPad).
   - Browser: Chrome, Safari, Firefox, Edge, atau browser modern berbasis WebKit/Blink.
   - Jaringan: Terhubung ke **jaringan Wi-Fi yang sama** dengan PC (disarankan frekuensi 5 GHz untuk performa optimal).

---

## 🚀 Panduan Instalasi & Menjalankan

### Langkah 1: Persiapan Awal
Pastikan driver ViGEmBus terpasang di Windows:
- Jika belum pernah memasang, buka folder `installers/` dan jalankan `ViGEmBus_1.22.0_x64_x86_arm64.exe`, lalu ikuti panduan instalasi di layar hingga selesai.

### Langkah 2: Setup Otomatis
1. Buka folder proyek.
2. Klik dua kali file **`setup.bat`**.
3. Script ini akan secara otomatis:
   - Mendeteksi apakah Anda memiliki `uv` atau `python`.
   - Membuat virtual environment `.venv`.
   - Memasang semua modul yang dibutuhkan dari `requirements.txt`.
   - Memeriksa status keberadaan driver ViGEmBus.

### Langkah 3: Pengaturan Firewall (Hanya Sekali)
Agar HP dapat terhubung ke server di PC via Wi-Fi lokal, port `8765` harus diizinkan lewat Windows Firewall:
- Klik kanan file **`enable-firewall.ps1`** → pilih **Run with PowerShell** (atau jalankan lewat PowerShell sebagai Administrator).
- Script ini hanya mengizinkan koneksi dari jaringan lokal (*LocalSubnet*), sehingga aman dan tidak mengekspos port ke internet.

### Langkah 4: Menjalankan Server
1. Klik dua kali file **`start.bat`**.
2. Jendela server akan aktif di background dan browser desktop otomatis terbuka ke:
   ```text
   http://127.0.0.1:8765/host
   ```
3. Di dashboard desktop akan muncul **QR Code Pairing**.

---

## 📱 Cara Menggunakan di HP

1. Buka kamera atau aplikasi pemindai QR di HP Anda, lalu arahkan ke QR Code yang ada di monitor PC.
2. Buka tautan yang muncul. Anda akan disambut oleh **Menu Utama Pocket Pad**:
   - Di bagian atas akan terlihat slot stik Anda (misal `01`) dan status koneksi (*Terhubung · XInput*).
   - Jika bermain bersama teman, pilih slot stik yang masih kosong (`01`, `02`, `03`, atau `04`).
3. **Mengatur Ukuran & Posisi Tombol**:
   - Tekan menu **Posisi & ukuran tombol**.
   - Ketuk tombol mana saja yang ingin diubah (tombol akan memiliki garis hijau neon).
   - Tekan **`＋`** untuk memperbesar, atau **`－`** untuk memperkecil (atau gunakan cubitan 2 jari langsung di layar).
   - Geser tombol ke tempat yang pas dengan jempol tangan Anda.
   - Tekan tombol centang **`✓`** untuk menyimpan.
4. **Mulai Bermain**:
   - Tekan tombol hijau **Run Gamepad**.
   - Putar HP ke posisi mendatar (*landscape*).
   - Layar seketika berubah menjadi gamepad murni layar penuh tanpa teks apa pun.
   - Buka game favorit Anda di PC (Steam, Emulator, Game Pass, dll). Game akan langsung mendeteksi stik Anda sebagai controller Xbox 360 resmi!
5. **Kembali ke Menu / Edit Saat Main**:
   - Tahan tombol **Home (ikon rumah)** selama 0,75 detik untuk kembali ke menu pengaturan kapan saja.

---

## 🔬 Spesifikasi Protokol Wire Format (16-Byte Binary)

Untuk menghilangkan overhead transmisi teks JSON dan meminimalkan garbage collection pada browser HP, Pocket Pad menggunakan transmisi biner terkompresi 16 byte per paket:

| Offset (Byte) | Tipe Data | Deskripsi |
|---|---|---|
| `0..1` | `uint16` (LE) | Magic Header `0x5044` (`'PD'`) |
| `2` | `uint8` | Flags status paket |
| `3` | `uint8` | Reserved (padding) |
| `4..5` | `uint16` (LE) | Bitmask status 15 tombol digital |
| `6..7` | `int16` (LE) | Left Stick X axis (-32768 s/d 32767) |
| `8..9` | `int16` (LE) | Left Stick Y axis (-32768 s/d 32767) |
| `10..11` | `int16` (LE) | Right Stick X axis (-32768 s/d 32767) |
| `12..13` | `int16` (LE) | Right Stick Y axis (-32768 s/d 32767) |
| `14` | `uint8` | Left Trigger / L2 (0 s/d 255) |
| `15` | `uint8` | Right Trigger / R2 (0 s/d 255) |

---

## 🧪 Pengujian Otomatis (Testing Suite)

Proyek ini dilengkapi pengujian menyeluruh (Unit Test, Integration Test, Playwright Browser Acceptance Test, dan Hardware XInput Verification):

```bat
:: Jalankan unit test Python
.venv\Scripts\python.exe -m pytest -q

:: Jalankan unit test protokol biner (Node.js)
node --test tests\input.test.cjs

:: Uji fitur perbesar/perkecil tombol di browser
.venv\Scripts\python.exe tests\verify_scaling.py

:: Uji alur menu & multi-slot controller
.venv\Scripts\python.exe tests\verify_menu.py

:: Uji drag & drop posisi tombol serta persistensi
.venv\Scripts\python.exe tests\verify_layout.py

:: Uji live touch browser langsung ke register Windows XInput
.venv\Scripts\python.exe tests\verify_live.py

:: Uji benchmark latensi transmisi
.venv\Scripts\python.exe tests\verify_latency.py
```

---

## ❓ Pemecahan Masalah (Troubleshooting)

- **HP tidak bisa membuka halaman saat scan QR code (ERR_CONNECTION_TIMED_OUT)**:
  - Pastikan HP dan PC terhubung ke Wi-Fi yang sama.
  - Jalankan script `enable-firewall.ps1` sebagai Administrator.
  - Periksa apakah router Anda mengaktifkan fitur *AP Isolation / Client Isolation* (jika aktif, perangkat tidak bisa saling kontak).
- **Status menunjukkan "Mode Diagnostik" bukan "XInput"**:
  - Driver ViGEmBus belum aktif atau belum diinstal. Jalankan file di `installers/ViGEmBus_1.22.0_x64_x86_arm64.exe`, restart PC jika diminta.
- **Game tidak merespons gerakan stik**:
  - Pastikan jendela game sedang aktif (fokus). Beberapa game PC membatasi pembacaan input stik jika jendela game diminimalkan.
- **Tampilan browser HP masih menampilkan address bar / tidak full**:
  - Di Android Chrome, sentuhan pertama saat klik *Run Gamepad* otomatis memicu fullscreen.
  - Di iOS Safari, tekan tombol **Share** → pilih **Add to Home Screen**. Buka dari ikon di layar depan HP agar berjalan dalam mode *standalone* 100% tanpa bar URL Safari.

---

## 📄 Lisensi

Proyek ini dilisensikan di bawah [MIT License](LICENSE). Bebas digunakan, dimodifikasi, dan didistribusikan.
