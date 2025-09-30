$ErrorActionPreference='Stop'

function Find-RepoRoot([string]$start) {
  if (-not $start) { $start = $PSScriptRoot }
  $cur = Resolve-Path -LiteralPath $start
  for ($i=0; $i -lt 12; $i++) {
    if (Test-Path (Join-Path $cur '.git')) { return $cur }
    $parent = Split-Path -Parent $cur
    if ($parent -eq $cur) { break }
    $cur = $parent
  }
  return (Get-Location).Path
}

$root = Find-RepoRoot $PSScriptRoot
$payload = Join-Path $PSScriptRoot '..\payload'
Write-Host "Applying payload from $payload to $root"

Copy-Item -Path (Join-Path $payload '*') -Destination $root -Recurse -Force

Push-Location $root
git checkout -B step/PA-360-lan-expose | Out-Null
git add -A
git commit -m "PA-360: add LAN server runner, firewall opener, and smokes" | Out-Null
git push -u origin step/PA-360-lan-expose

# run smoke
python -m pytest -q tests\smoke\test_lan_server_boot.py
$code = $LASTEXITCODE
Pop-Location
if ($code -ne 0) { throw "smoke failed ($code)" }
Write-Host "PA-360 applied & smokes passed."
Write-Host "Start the LAN server with:"
Write-Host "  pwsh tools\ps1\run_control_server_lan.ps1"
exit 0
