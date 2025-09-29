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
git checkout -B step/PA-342-blueprint-paths | Out-Null
git add -A
git commit -m "PA-342: fix duplicated blueprint prefixes; add path smokes" | Out-Null
git push -u origin step/PA-342-blueprint-paths

# quick smoke
$env:PA_JOB_DUMMY = '1'
python -m pytest -q tests\smoke\test_blueprint_paths.py
$code = $LASTEXITCODE
Pop-Location
if ($code -ne 0) { throw "smoke failed ($code)" }
Write-Host "PA-342 applied & smokes passed."
exit 0
