# Pocket Pad

Gamepad web layar penuh di HP → WebSocket biner lokal → controller virtual Xbox 360 / XInput di Windows.

## Cara Menggunakan

1. Jalankan **start.bat** di komputer (atau jalankan `.venv\Scripts\python.exe launch.py`).
2. Dashboard desktop terbuka di: `http://127.0.0.1:8765/host`.
3. Hubungkan HP dan PC ke jaringan Wi-Fi yang sama (disarankan 5 GHz untuk latensi minimal).
4. Scan QR code yang tampil di dashboard desktop menggunakan kamera HP.
5. Di HP akan muncul **Tampilan Menu**:
   - Menampilkan slot stik Anda (misal `01`) dan jumlah HP yang terhubung (`1 / 4 terhubung`).
   - Bisa memilih nomor slot stik (01, 02, 03, 04).
   - Menampilkan statistik ping dan RTT input real-time.
   - **Posisi & ukuran tombol**: geser posisi dan atur ukuran setiap tombol / analog.
   - **Mapping tombol**: remap tombol, deadzone, tukar analog kiri/kanan, serta slider ukuran tombol default.
   - Tombol **Run Gamepad**: langsung masuk ke tampilan murni gamepad dan meminta layar penuh (fullscreen).
6. Saat bermain di gamepad:
   - Tampilan bersih murni gamepad tanpa teks/header.
   - Tahan tombol **Home (ikon rumah)** selama 0,75 detik jika ingin kembali ke menu atau mengubah posisi/ukuran tombol.

## Fitur Perbesar / Ubah Ukuran Tombol

1. **Per tombol / individual (di mode edit "Posisi & ukuran tombol"):**
   - Ketuk tombol atau analog yang ingin diubah ukurannya hingga muncul garis penanda hijau.
   - Tekan tombol **`＋`** di toolbar bawah untuk memperbesar ukuran (hingga 220%).
   - Tekan tombol **`－`** untuk memperkecil ukuran (hingga 60%).
   - Indikator persentase ukuran (misal `130%`) tampil di tengah toolbar.
   - **Gesture 2 jari (Pinch to Zoom):** Anda juga bisa langsung meletakkan 2 jari di atas tombol/layar lalu cubit (pinch in/out) untuk memperbesar atau memperkecil secara fleksibel!
   - Tekan tombol **`✓`** untuk menyimpan. Posisi dan ukuran tersimpan otomatis di HP.
   - Tekan tombol **`↺`** untuk reset posisi dan ukuran kembali ke 100%.
2. **Semua tombol sekaligus (di menu "Mapping tombol"):**
   - Terdapat slider **Ukuran semua tombol** (70% - 170%).
   - Terdapat slider **Ukuran analog stik** (70% - 170%).
   - Cocok jika Anda ingin semua tombol langsung berukuran lebih besar tanpa harus mengatur satu per satu.

## Optimasi Latensi & Realtime

- **Paket Biner Ringkas (16-byte):** Data input dikirim dalam format biner ArrayBuffer 16-byte (mask tombol uint16, 4 analog int16, trigger uint8, sequence uint32), bukan JSON string yang berat.
- **TCP_NODELAY & Zero Compression:** Menghilangkan delay buffering Nagle algorithm pada socket.
- **Event-Driven Instant Send:** Input tombol dikirim seketika saat event pointer menyentuh layar tanpa polling delay.
- **Pointer Raw Update & Coalesced Events:** Analog stik membaca sensor sentuh layar secara presisi tinggi dengan pemrosesan sub-milidetik.
- **Watchdog Auto-Reset:** Input netral otomatis jika koneksi terputus mendadak (< 500 ms) agar tombol tidak tersangkut di dalam game.

## Pengujian Otomatis

```bat
.venv\Scripts\python.exe -m pytest -q
node --test tests\input.test.cjs
.venv\Scripts\python.exe tests\verify_scaling.py
.venv\Scripts\python.exe tests\verify_menu.py
.venv\Scripts\python.exe tests\verify_layout.py
.venv\Scripts\python.exe tests\verify_live.py
.venv\Scripts\python.exe tests\verify_latency.py
```
