@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
title Pocket Pad - Installer & Shortcut Creator

echo ===================================================================
echo             POCKET PAD - WINDOWS APP INSTALLER
echo ===================================================================
echo.

:: 1. Check Gamepad.exe
if not exist "Gamepad.exe" (
    echo [ERROR] Gamepad.exe tidak ditemukan di folder ini!
    echo Pastikan Anda mengekstrak semua file dari paket Pocket Pad.
    pause
    exit /b 1
)

:: 2. Check & Install ViGEmBus Driver
echo [1/3] Memeriksa driver ViGEmBus (XInput Virtual Controller)...
if exist "%SystemRoot%\System32\drivers\ViGEmBus.sys" (
    echo       [OK] Driver ViGEmBus sudah terpasang.
) else (
    echo       [*] Driver belum terpasang. Menjalankan installer resmi ViGEmBus...
    if exist "installers\ViGEmBus_1.22.0_x64_x86_arm64.exe" (
        start /wait "" "installers\ViGEmBus_1.22.0_x64_x86_arm64.exe"
    ) else (
        echo       [!] File installer ViGEmBus tidak ditemukan di folder installers\
    )
)
echo.

:: 3. Setup Firewall Rule
echo [2/3] Mengatur Windows Firewall untuk koneksi Wi-Fi HP (Port 8765)...
powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process powershell -Verb RunAs -Wait -ArgumentList '-NoProfile -ExecutionPolicy Bypass -File \"\"%~dp0enable-firewall.ps1\"\"'"
echo       [OK] Pengaturan firewall selesai.
echo.

:: 4. Create Desktop & Start Menu Shortcuts
echo [3/3] Membuat Shortcut di Desktop dan Start Menu...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0create_shortcut.ps1" -TargetDir "%~dp0"
echo.

echo ===================================================================
echo  Instalasi selesai! Shortcut "Pocket Pad" sudah ada di Desktop Anda.
echo ===================================================================
echo.

set /p RUN_NOW="Jalankan Pocket Pad sekarang? (Y/N, default Y): "
if /i "%RUN_NOW%"=="N" (
    echo Anda dapat menjalankan Pocket Pad kapan saja lewat shortcut di Desktop.
) else (
    start "" "%~dp0Gamepad.exe"
)

echo.
pause
