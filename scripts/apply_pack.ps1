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

# Inject Status card into mobile page
pwsh (Join-Path $root 'scripts\inject_status_card.ps1')

Push-Location $root
git checkout -B step/PA-370-desktop-suite | Out-Null
git add -A
git commit -m "PA-370: desktop suite launcher, status API, mobile status card, smokes" | Out-Null
git push -u origin step/PA-370-desktop-suite

# run smokes
python -m pytest -q tests\smoke\test_status_api_json.py
$code = $LASTEXITCODE
Pop-Location
if ($code -ne 0) { throw "smoke failed ($code)" }

Write-Host "PA-370 applied & smokes passed."
Write-Host "Start everything with:  pwsh tools\ps1\run_desktop_suite.ps1"
Write-Host "Stop jobs with:         pwsh tools\ps1\stop_desktop_suite.ps1"
exit 0
