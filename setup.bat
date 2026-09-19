@echo off
cd /d "%~dp0"
where uv >nul 2>&1
if errorlevel 1 (
  echo Install uv dari https://docs.astral.sh/uv/getting-started/installation/
  pause
  exit /b 1
)
echo Pasang ViGEmBus resmi terlebih dahulu. vgamepad dapat membuka installer driver bila driver belum ada.
if not exist ".venv\Scripts\python.exe" uv venv .venv
uv pip install --python .venv\Scripts\python.exe -r requirements.txt
if errorlevel 1 (
  pause
  exit /b 1
)
echo Selesai. Buka start.bat.
pause
