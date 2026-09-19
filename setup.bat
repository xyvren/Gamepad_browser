@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo ===================================================
echo             Pocket Pad - Setup Script
echo ===================================================
echo.

:: 1. Check Python / uv
set "HAS_UV=0"
where uv >nul 2>&1 && set "HAS_UV=1"

set "HAS_PY=0"
where python >nul 2>&1 && set "HAS_PY=1"

if "%HAS_UV%"=="0" if "%HAS_PY%"=="0" (
    echo [ERROR] Python tidak ditemukan di sistem ini!
    echo Silakan install Python 3.10+ dari https://www.python.org/downloads/
    echo atau install uv dari https://docs.astral.sh/uv/
    echo Pastikan centang "Add Python to PATH" saat instalasi.
    pause
    exit /b 1
)

:: 2. Setup Virtual Environment
if not exist ".venv\Scripts\python.exe" (
    echo [*] Membuat virtual environment (.venv)...
    if "%HAS_UV%"=="1" (
        uv venv .venv
    ) else (
        python -m venv .venv
    )
)

:: 3. Install Dependencies
echo [*] Memasang dependencies dari requirements.txt...
if "%HAS_UV%"=="1" (
    uv pip install --python .venv\Scripts\python.exe -r requirements.txt
) else (
    .venv\Scripts\python.exe -m pip install --upgrade pip
    .venv\Scripts\pip.exe install -r requirements.txt
)

if errorlevel 1 (
    echo [ERROR] Gagal memasang dependensi Python.
    pause
    exit /b 1
)

:: 4. Check ViGEmBus Driver
echo.
echo [*] Memeriksa driver ViGEmBus...
if exist "%SystemRoot%\System32\drivers\ViGEmBus.sys" (
    echo [OK] Driver ViGEmBus terdeteksi terpasang.
) else (
    echo [PERHATIAN] Driver ViGEmBus belum terpasang.
    if exist "installers\ViGEmBus_1.22.0_x64_x86_arm64.exe" (
        echo [*] Menjalankan installer resmi ViGEmBus...
        start "" "installers\ViGEmBus_1.22.0_x64_x86_arm64.exe"
    ) else (
        echo Silakan unduh driver ViGEmBus dari:
        echo https://github.com/nefarius/ViGEmBus/releases/tag/v1.22.0
    )
)

echo.
echo ===================================================
echo  Setup selesai! Jalankan start.bat untuk mulai.
echo ===================================================
echo.
pause
