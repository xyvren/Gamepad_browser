$ErrorActionPreference = 'Stop'
$existing = Get-NetFirewallRule -DisplayName 'Pocket Pad LAN' -ErrorAction SilentlyContinue
if ($existing) {
    Set-NetFirewallRule -DisplayName 'Pocket Pad LAN' -Direction Inbound -Action Allow -Protocol TCP -LocalPort 8765,8766 -RemoteAddress LocalSubnet -Profile Any | Out-Null
} else {
    New-NetFirewallRule -DisplayName 'Pocket Pad LAN' -Direction Inbound -Action Allow -Protocol TCP -LocalPort 8765,8766 -RemoteAddress LocalSubnet -Profile Any | Out-Null
}
Get-NetFirewallRule -DisplayName 'Pocket Pad LAN' | Format-List DisplayName,Enabled,Direction,Action
