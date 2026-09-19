# PowerShell script to create Desktop and Start Menu shortcuts for Pocket Pad
param (
    [string]$TargetDir = $PSScriptRoot
)

$ErrorActionPreference = 'Stop'
$WshShell = New-Object -ComObject WScript.Shell

$ExePath = Join-Path $TargetDir "Gamepad.exe"
$IconPath = Join-Path $TargetDir "icon.ico"

if (-not (Test-Path $ExePath)) {
    Write-Error "Gamepad.exe tidak ditemukan di: $TargetDir"
    exit 1
}

# 1. Desktop Shortcut
$DesktopPath = [Environment]::GetFolderPath('Desktop')
$DesktopShortcutPath = Join-Path $DesktopPath "Pocket Pad.lnk"
$DesktopShortcut = $WshShell.CreateShortcut($DesktopShortcutPath)
$DesktopShortcut.TargetPath = $ExePath
$DesktopShortcut.WorkingDirectory = $TargetDir
$DesktopShortcut.Description = "Pocket Pad - Virtual Gamepad Desktop"
if (Test-Path $IconPath) {
    $DesktopShortcut.IconLocation = "$IconPath,0"
} else {
    $DesktopShortcut.IconLocation = "$ExePath,0"
}
$DesktopShortcut.Save()
Write-Host "[OK] Shortcut Desktop berhasil dibuat: $DesktopShortcutPath"

# 2. Start Menu Shortcut
$ProgramsPath = [Environment]::GetFolderPath('Programs')
$StartMenuShortcutPath = Join-Path $ProgramsPath "Pocket Pad.lnk"
$StartMenuShortcut = $WshShell.CreateShortcut($StartMenuShortcutPath)
$StartMenuShortcut.TargetPath = $ExePath
$StartMenuShortcut.WorkingDirectory = $TargetDir
$StartMenuShortcut.Description = "Pocket Pad - Virtual Gamepad Desktop"
if (Test-Path $IconPath) {
    $StartMenuShortcut.IconLocation = "$IconPath,0"
} else {
    $StartMenuShortcut.IconLocation = "$ExePath,0"
}
$StartMenuShortcut.Save()
Write-Host "[OK] Shortcut Start Menu berhasil dibuat: $StartMenuShortcutPath"
