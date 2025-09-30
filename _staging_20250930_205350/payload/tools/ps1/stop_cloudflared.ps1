Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
Get-Process cloudflared -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Write-Host "[CF] cloudflared stopped (if running)"
