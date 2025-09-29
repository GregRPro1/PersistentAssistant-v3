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
git checkout -B step/PA-343-mobile-template-fix | Out-Null
git add -A
git commit -m "PA-343: fix Template collision in mobile_home; /app/ returns 200" | Out-Null
git push -u origin step/PA-343-mobile-template-fix

# Write a small smoke to disk and execute it (PowerShell-safe)
$smoke = @"
import importlib
from flask import Flask
m = importlib.import_module('server.mobile_home')
app = Flask('t'); app.register_blueprint(m.bp, url_prefix=m.mount_path)
r = app.test_client().get('/app/')
assert r.status_code==200, r.status_code
print('OK /app/')
"@
$smokePath = Join-Path $root "tmp\smoke_mobile.py"
New-Item -ItemType Directory -Force -Path (Split-Path $smokePath) | Out-Null
Set-Content -Path $smokePath -Value $smoke -Encoding UTF8
python $smokePath
$code = $LASTEXITCODE
Pop-Location
if ($code -ne 0) { throw "mobile smoke failed ($code)" }
Write-Host "PA-343 applied & mobile smoke passed."
exit 0
