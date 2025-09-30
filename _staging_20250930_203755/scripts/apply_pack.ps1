<# 
PA-361 FIX3 — Self-contained pack
This pack's scripts\apply_pack.ps1 performs ALL actions directly:
- Surgical test/import fix
- Remove payload\tests
- Ensure pytest.ini (exclude noisy dirs)
- Clear caches
- Run pytest -m smoke (single run) and print a SHORT summary
- Attempt tunnel bring-up (best-effort)
- Git commit (no push)
Compatible with your one-liner runner.
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Timestamp { (Get-Date).ToString('yyyyMMdd_HHmmss') }
function Ensure-Dir([string]$p){ if (-not (Test-Path $p)) { New-Item -ItemType Directory -Force -Path $p | Out-Null } }
function Backup-File([string]$f, [string]$backupDir) { if (Test-Path $f) { $dest = Join-Path $backupDir (Split-Path $f -Leaf); Copy-Item -Force -Path $f -Destination $dest } }

# Repo root is parent of this scripts dir
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot  = Split-Path -Parent $ScriptDir
Push-Location $RepoRoot
Write-Host "apply_pack: repo root = $RepoRoot"

$ts = Timestamp
Ensure-Dir "tmp"
$backupDir = Join-Path "tmp" ("patch_backup_" + $ts)
Ensure-Dir $backupDir
Ensure-Dir "tmp\logs"
Ensure-Dir "reports\ops"

# 1) Fix tests/smoke/test_graph_config.py import (idempotent)
$testGraph = Join-Path 'tests\smoke' 'test_graph_config.py'
if (Test-Path $testGraph) {
  Backup-File $testGraph $backupDir
  $content = Get-Content $testGraph -Raw
  if ($content -match "from pathlib import Path,\s*re") {
    $new = $content -replace "from pathlib import Path,\s*re", "from pathlib import Path`r`nimport re"
    Set-Content -Encoding UTF8 -Path $testGraph -Value $new
    Write-Host "[PACK] Fixed bad import in tests/smoke/test_graph_config.py"
  } else {
    Write-Host "[PACK] test_graph_config import OK"
  }
} else {
  Write-Host "[PACK] tests/smoke/test_graph_config.py not found — skipping"
}

# 2) Remove payload\tests to prevent pytest dup import
$payloadTests = Join-Path 'payload' 'tests'
if (Test-Path $payloadTests) {
  $dest = Join-Path $backupDir 'payload_tests_backup'
  Copy-Item -Recurse -Force -Path $payloadTests -Destination $dest
  Remove-Item -Recurse -Force -Path $payloadTests
  Write-Host "[PACK] Removed payload\tests (backed up)"
}

# 3) Ensure pytest.ini excludes noisy dirs
$pytestIni = "pytest.ini"
$pytestBody = @"
[pytest]
norecursedirs = payload .venv tmp _staging _packs _staging_* _packs_* build dist
"@
if (-not (Test-Path $pytestIni)) {
  Set-Content -Encoding UTF8 -Path $pytestIni -Value $pytestBody
  Backup-File $pytestIni $backupDir
  Write-Host "[PACK] Wrote pytest.ini"
} else {
  $cur = Get-Content $pytestIni -Raw
  if ($cur -notmatch "norecursedirs") {
    $cur += "`r`n" + $pytestBody
    Set-Content -Encoding UTF8 -Path $pytestIni -Value $cur
    Backup-File $pytestIni $backupDir
    Write-Host "[PACK] Updated pytest.ini (added norecursedirs)"
  } else {
    Write-Host "[PACK] pytest.ini present"
  }
}

# 4) Clear py caches
Get-ChildItem -Recurse -Force -Filter "__pycache__" -ErrorAction SilentlyContinue | ForEach-Object { Remove-Item -Recurse -Force -Path $_.FullName -ErrorAction SilentlyContinue }
Get-ChildItem -Recurse -Force -Include *.pyc -ErrorAction SilentlyContinue | ForEach-Object { Remove-Item -Force -Path $_.FullName -ErrorAction SilentlyContinue }

# 5) Run smokes once
$pytestLog = "tmp\logs\pytest_smoke_$ts.txt"
$smokeSummary = "$env:TEMP\pytest_smoke_summary_$ts.txt"
Write-Host "[PACK] Running pytest -q -m smoke"
$exit = 0
try {
  & python -m pytest -q -m smoke *>&1 | Tee-Object -FilePath $pytestLog
  $exit = $LASTEXITCODE
} catch {
  $exit = 1
}
# Extract last 15 lines as a short summary
if (Test-Path $pytestLog) {
  (Get-Content $pytestLog -Tail 15) | Set-Content -Encoding UTF8 -Path $smokeSummary
  Write-Host "---- PyTest (tail) ----"
  Get-Content $smokeSummary | ForEach-Object { Write-Host $_ }
  Write-Host "------------------------"
}

# 6) Try to run tunnel helpers (best-effort)
$install = 'tools\ps1\install_cloudflared.ps1'
$tunnel  = 'tools\ps1\run_quick_tunnel.ps1'
if (Test-Path $install) { try { pwsh -NoProfile -ExecutionPolicy Bypass -File $install } catch {} }
if (Test-Path $tunnel)  { try { pwsh -NoProfile -ExecutionPolicy Bypass -File $tunnel  } catch {} }

# Report endpoints
if (Test-Path 'reports\ops\tunnel_url.txt') {
  Write-Host "[PACK] Tunnel URL:"
  Get-Content 'reports\ops\tunnel_url.txt' | ForEach-Object { Write-Host "    $_" }
} else {
  Write-Host "[PACK] No tunnel_url.txt yet"
}
try {
  $api = Invoke-RestMethod -Uri http://127.0.0.1:8776/api/tunnel -Method Get -TimeoutSec 3
  Write-Host "[PACK] /api/tunnel:"
  $api | ConvertTo-Json -Depth 4 | Write-Host
} catch {}

# 7) Commit (no push)
try {
  git add -A
  git commit -m "PA-361 FIX3: smokes run once + pytest.ini + import fix + tunnel checks" | Out-Null
  Write-Host "[PACK] Commit created (or nothing to commit)"
} catch {
  Write-Host "[PACK] Git commit failed (possibly no changes)"
}

# Final concise summary
Write-Host "==== PACK SUMMARY ===="
Write-Host ("Repo: " + $RepoRoot)
Write-Host ("PyTest exit: " + $exit)
Write-Host ("Log: tmp\logs\pytest_smoke_" + $ts + ".txt")
if (Test-Path 'reports\ops\tunnel_url.txt') {
  $u = (Get-Content 'reports\ops\tunnel_url.txt' -TotalCount 1)
  Write-Host ("Tunnel: " + $u)
} else {
  Write-Host "Tunnel: (no URL file)"
}
Write-Host "======================"
