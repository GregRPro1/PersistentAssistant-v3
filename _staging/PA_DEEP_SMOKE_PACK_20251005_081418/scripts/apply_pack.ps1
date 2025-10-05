# scripts\apply_pack.ps1
# Minimal pack applier: install deep_smoke.ps1 into tools\ps1 (repo root assumed as current location).

$ErrorActionPreference = 'Stop'

function Copy-Into([string]$src, [string]$dst){
    $dstDir = Split-Path -Parent $dst
    if (-not (Test-Path $dstDir)){ New-Item -ItemType Directory -Force $dstDir | Out-Null }
    Copy-Item -LiteralPath $src -Destination $dst -Force
    Write-Host ("Updated {0}" -f $dst)
}

$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$payloadDeep = Join-Path $here '..\tools\ps1\deep_smoke.ps1'
$destDeep    = Join-Path (Get-Location) 'tools\ps1\deep_smoke.ps1'

Copy-Into $payloadDeep $destDeep

Write-Host "==== Deep Smoke pack applied ===="
Write-Host "Run (analysis only):  pwsh tools\ps1\deep_smoke.ps1"
Write-Host "Run (with recovery):  pwsh tools\ps1\deep_smoke.ps1 -Restart"
