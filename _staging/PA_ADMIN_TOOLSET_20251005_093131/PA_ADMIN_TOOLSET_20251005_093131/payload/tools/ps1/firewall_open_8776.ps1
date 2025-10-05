
$principal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
$admin = $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $admin) {
  Write-Host "Please run this script in an elevated PowerShell (Run as Administrator)."
  exit 1
}

try {
  $rule = Get-NetFirewallRule -DisplayName "PA Watchdog 8776" -ErrorAction SilentlyContinue
  if ($rule) { Write-Host "Firewall rule already exists."; exit 0 }
  New-NetFirewallRule -DisplayName "PA Watchdog 8776" -Direction Inbound -LocalPort 8776 -Protocol TCP -Action Allow -Profile Any | Out-Null
  Write-Host "Firewall rule created."
} catch {
  Write-Host ("Firewall rule creation failed: {0}" -f $_.Exception.Message)
  exit 1
}
