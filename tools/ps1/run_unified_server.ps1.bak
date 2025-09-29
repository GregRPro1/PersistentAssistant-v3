param([string]$Host='127.0.0.1', [int]$Port=8765)
$ErrorActionPreference='Stop'
function Find-RepoRoot([string]$start) {
  if (-not $start) { $start = $PSScriptRoot }
  $cur = Resolve-Path -LiteralPath $start
  for ($i=0; $i -lt 10; $i++) {
    if (Test-Path (Join-Path $cur '.git')) { return $cur }
    $parent = Split-Path -Parent $cur
    if ($parent -eq $cur) { break }
    $cur = $parent
  }
  return (Get-Location).Path
}
$root = Find-RepoRoot $null
Write-Host "Unified server root: $root"
$env:FLASK_ENV = "production"
if ($Host) { $env:PA_UNIFIED_HOST = $Host }
if ($Port) { $env:PA_UNIFIED_PORT = $Port }
& python (Join-Path $root 'tools\py\unified_server.py')