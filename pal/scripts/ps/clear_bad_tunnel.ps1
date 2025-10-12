Set-StrictMode -Version Latest
$ErrorActionPreference = "Continue"
$opsPath = ".\reports\ops\ops_status.json"; $tunFile = ".\reports\ops\tunnel_url.txt"
if (Test-Path $tunFile) { "" | Set-Content $tunFile -Encoding UTF8 }
if (Test-Path $opsPath) {
  $ops = Get-Content -Raw $opsPath | ConvertFrom-Json
  if (-not $ops.tunnel) { $ops | Add-Member -NotePropertyName tunnel -NotePropertyValue ([pscustomobject]@{}) -Force }
  $ops.tunnel.url = ""; $ops.tunnel.ok = $false
  if (-not $ops.phone) { $ops | Add-Member -NotePropertyName phone -NotePropertyValue ([pscustomobject]@{}) -Force }
  if ($ops.phone.lan) { $ops.phone.url = $ops.phone.lan }
  $ops.ts = (Get-Date).ToString("s")
  $ops | ConvertTo-Json -Depth 6 | Set-Content $opsPath -Encoding UTF8
  Write-Host "Cleared tunnel; Phone now -> $($ops.phone.url)"
} else { Write-Host "ops_status.json not found; nothing to clear." }