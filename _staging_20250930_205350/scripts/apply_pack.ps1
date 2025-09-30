<# 
PA-361 FIX4 — Single-pass, no recursion
- Normalize pytest.ini (single [pytest])
- Fix test import
- Remove payload\tests
- Clear caches
- Run pytest -m smoke; emit summary
- Overwrite Cloudflare scripts (install/run/stop) with robust versions from payload
- Try tunnel bring-up (best-effort)
- Commit changes (no push)
#>
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Timestamp { (Get-Date).ToString('yyyyMMdd_HHmmss') }
function Ensure-Dir([string]$p){ if (-not (Test-Path $p)) { New-Item -ItemType Directory -Force -Path $p | Out-Null } }
function Backup-File([string]$f, [string]$backupDir) { if (Test-Path $f) { $dest = Join-Path $backupDir (Split-Path $f -Leaf); Copy-Item -Force -Path $f -Destination $dest } }

# Repo root is parent of scripts dir
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

# 0) Overwrite Cloudflare scripts from payload (stable behavior)
$payloadRoot = Join-Path $ScriptDir "..\payload" | Resolve-Path -ErrorAction SilentlyContinue
if ($payloadRoot) {
  Write-Host "[PACK] Installing Cloudflare helper scripts"
  $pairs = @{
    (Join-Path $payloadRoot.Path 'tools\ps1\install_cloudflared.ps1') = 'tools\ps1\install_cloudflared.ps1';
    (Join-Path $payloadRoot.Path 'tools\ps1\run_quick_tunnel.ps1')    = 'tools\ps1\run_quick_tunnel.ps1';
    (Join-Path $payloadRoot.Path 'tools\ps1\stop_cloudflared.ps1')    = 'tools\ps1\stop_cloudflared.ps1';
  }
  foreach ($k in $pairs.Keys) {
    $dest = $pairs[$k]
    Ensure-Dir (Split-Path $dest -Parent)
    Backup-File $dest $backupDir
    Copy-Item -Force -Path $k -Destination $dest
  }
}

# 1) Normalize pytest.ini
$pytestIni = "pytest.ini"
$norecurse = "norecursedirs = payload .venv tmp _staging _packs _staging_* _packs_* build dist"
$ini_body = @"
[pytest]
$norecurse
"@
if (-not (Test-Path $pytestIni)) {
  Set-Content -Encoding UTF8 -Path $pytestIni -Value $ini_body
  Write-Host "[PACK] Created pytest.ini"
} else {
  $raw = Get-Content $pytestIni -Raw
  # Strip all existing [pytest] sections and rebuild single section
  $clean = $raw -replace '(\[pytest\][\s\S]*?$)',''
  $final = $ini_body
  Set-Content -Encoding UTF8 -Path $pytestIni -Value $final
  Write-Host "[PACK] Normalized pytest.ini"
}
Backup-File $pytestIni $backupDir

# 2) Fix tests/smoke/test_graph_config.py import
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
}

# 3) Remove payload\tests to prevent pytest dup import
$payloadTests = Join-Path 'payload' 'tests'
if (Test-Path $payloadTests) {
  $dest = Join-Path $backupDir 'payload_tests_backup'
  Copy-Item -Recurse -Force -Path $payloadTests -Destination $dest
  Remove-Item -Recurse -Force -Path $payloadTests
  Write-Host "[PACK] Removed payload\tests (backed up)"
}

# 4) Clear python caches
Get-ChildItem -Recurse -Force -Filter "__pycache__" -ErrorAction SilentlyContinue | ForEach-Object { Remove-Item -Recurse -Force -Path $_.FullName -ErrorAction SilentlyContinue }
Get-ChildItem -Recurse -Force -Include *.pyc -ErrorAction SilentlyContinue | ForEach-Object { Remove-Item -Force -Path $_.FullName -ErrorAction SilentlyContinue }

# 5) Run smokes once, short summary
$pytestLog = "tmp\logs\pytest_smoke_$ts.txt"
$exit = 0
Write-Host "[PACK] Running pytest -q -m smoke"
try {
  & python -m pytest -q -m smoke *>&1 | Tee-Object -FilePath $pytestLog
  $exit = $LASTEXITCODE
} catch { $exit = 1 }
if (Test-Path $pytestLog) {
  Write-Host "---- PyTest (tail) ----"
  Get-Content $pytestLog -Tail 25 | ForEach-Object { Write-Host $_ }
  Write-Host "------------------------"
}

# 6) Try Cloudflare quick tunnel (best-effort)
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
  git commit -m "PA-361 FIX4: normalize pytest.ini; import fix; cloudflared helpers; smoke and tunnel checks" | Out-Null
  Write-Host "[PACK] Commit created (or nothing to commit)"
} catch {
  Write-Host "[PACK] Git commit failed (possibly no changes)"
}

# Summary
Write-Host "==== PACK SUMMARY ===="
Write-Host ("Repo: " + $RepoRoot)
Write-Host ("PyTest exit: " + $exit)
Write-Host ("Log: tmp\logs\pytest_smoke_" + $ts + ".txt")
if (Test-Path 'reports\ops\tunnel_url.txt') {
  $u = (Get-Content 'reports\ops\tunnel_url.txt' -TotalCount 1)
  Write-Host ("Tunnel: " + $u)
} else { Write-Host "Tunnel: (no URL file)" }
Write-Host "======================"
