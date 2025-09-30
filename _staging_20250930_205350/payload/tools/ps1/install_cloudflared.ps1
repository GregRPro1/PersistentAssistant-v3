param(
  [string]$BinDir = (Join-Path $PSScriptRoot '..\bin')
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

Write-Host "[CF] install_cloudflared: checking availability"
# Respect existing install in PATH or local bin
$exe = (Get-Command cloudflared -ErrorAction SilentlyContinue)
if ($exe) {
  Write-Host "[CF] cloudflared found at $($exe.Source)"
  exit 0
}

$local = Join-Path $BinDir 'cloudflared.exe'
if (Test-Path $local) {
  # add local bin to PATH for this session
  $env:PATH = $BinDir + [System.IO.Path]::PathSeparator + $env:PATH
  Write-Host "[CF] cloudflared found in $BinDir"
  exit 0
}

Write-Warning "[CF] cloudflared not found in PATH or $BinDir. Install it and rerun run_quick_tunnel.ps1."
exit 0
