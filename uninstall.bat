@echo off
setlocal
cd /d "%~dp0"
title Pocket Pad - Uninstaller

echo ===================================================================
echo               POCKET PAD - UNINSTALL SHORTCUTS
echo ===================================================================
echo.

set /p CONFIRM="Hapus shortcut Desktop, Start Menu, dan rule Firewall? (Y/N): "
if /i not "%CONFIRM%"=="Y" (
    echo Dibatalkan.
    exit /b 0
)

:: 1. Remove Desktop Shortcut
if exist "%USERPROFILE%\Desktop\Pocket Pad.lnk" (
    del /f /q "%USERPROFILE%\Desktop\Pocket Pad.lnk"
    echo [OK] Shortcut Desktop dihapus.
)

:: 2. Remove Start Menu Shortcut
if exist "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Pocket Pad.lnk" (
    del /f /q "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Pocket Pad.lnk"
    echo [OK] Shortcut Start Menu dihapus.
)

:: 3. Remove Firewall Rule
powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process powershell -Verb RunAs -Wait -ArgumentList '-Command Remove-NetFirewallRule -DisplayName \"\"Pocket Pad LAN\"\" -ErrorAction SilentlyContinue'"
echo [OK] Rule Firewall dihapus.

echo.
echo Selesai.
pause
