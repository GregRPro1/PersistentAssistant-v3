param([int]$Port=8776,[string]$Name="PA Control 8776")
$ErrorActionPreference='Stop'
try {
  $existing = Get-NetFirewallRule -DisplayName $Name -ErrorAction SilentlyContinue
  if (-not $existing) {
    New-NetFirewallRule -DisplayName $Name -Direction Inbound -Action Allow -Protocol TCP -LocalPort $Port | Out-Null
    Write-Host "Firewall: opened TCP $Port ($Name)"
  } else {
    Write-Host "Firewall: rule '$Name' already exists"
  }
} catch {
  Write-Warning "Firewall rule creation failed (need admin?). You may manually allow inbound TCP $Port."
}
