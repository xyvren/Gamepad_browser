$ErrorActionPreference = 'Stop'
$existing = Get-NetFirewallRule -DisplayName 'Pocket Pad LAN' -ErrorAction SilentlyContinue
if (-not $existing) {
    New-NetFirewallRule -DisplayName 'Pocket Pad LAN' -Direction Inbound -Action Allow -Protocol TCP -LocalPort 8765 -RemoteAddress LocalSubnet -Profile Any | Out-Null
}
Get-NetFirewallRule -DisplayName 'Pocket Pad LAN' | Format-List DisplayName,Enabled,Direction,Action
