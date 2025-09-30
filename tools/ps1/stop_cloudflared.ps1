param([string]$OutDir = (Join-Path $PSScriptRoot '..\..\reports\ops'))
$ErrorActionPreference = 'Stop'
$pidFile = Join-Path $OutDir 'cloudflared.pid'
if (Test-Path $pidFile) {
  $pid = (Get-Content $pidFile -Raw).Trim()
  if ($pid) { try { Stop-Process -Id [int]$pid -Force } catch {} }
  Remove-Item -Force $pidFile -ErrorAction SilentlyContinue
}
Write-Host "cloudflared stopped (if running)"
exit 0
