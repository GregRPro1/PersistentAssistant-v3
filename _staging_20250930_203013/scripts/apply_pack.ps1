<# 
PA-361 Fix Pack (smokes + tunnel + commit)
Pack style: compatible with apply_packs_only.ps1 (looks for scripts\apply_pack.ps1)
This script makes minimal, surgical changes, runs smokes, optional tunnel bring-up, and commits.
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Timestamp() { (Get-Date).ToString('yyyyMMdd_HHmmss') }
function Ensure-Dir($p){ if (-not (Test-Path $p)) { New-Item -ItemType Directory -Force -Path $p | Out-Null } }
function Backup-File($f, $backupDir) { if (Test-Path $f) { $dest = Join-Path $backupDir (Split-Path $f -Leaf); Copy-Item -Force -Path $f -Destination $dest } }

# Determine repo root (apply_packs_only.ps1 extracts under _staging; repo root is the parent of scripts dir)
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot  = Split-Path -Parent $ScriptDir
Push-Location $RepoRoot

Write-Host "apply_pack: repo root = $RepoRoot"

# Optional: copy payload contents into repo (if present)
$payloadDir = Join-Path $ScriptDir '..\payload' | Resolve-Path -ErrorAction SilentlyContinue
if ($payloadDir) {
  Write-Host "Applying payload from $payloadDir to $RepoRoot"
  $items = Get-ChildItem -Recurse $payloadDir
  foreach ($it in $items) {
    if ($it.PSIsContainer) { continue }
    $rel = $it.FullName.Substring($payloadDir.Path.Length).TrimStart('\','/')
    $dest = Join-Path $RepoRoot $rel
    Ensure-Dir (Split-Path $dest -Parent)
    Copy-Item -Force -Path $it.FullName -Destination $dest
  }
} else {
  Write-Host "No payload dir in this pack — proceeding with scripted edits"
}

# Backups & logs
$ts = Timestamp()
Ensure-Dir "tmp"
$backupDir = Join-Path "tmp" ("patch_backup_" + $ts)
Ensure-Dir $backupDir
Ensure-Dir "tmp\logs"
Ensure-Dir "reports\ops"

# ---- Fix tests/smoke/test_graph_config.py import ----
$testGraph = Join-Path 'tests\smoke' 'test_graph_config.py'
if (Test-Path $testGraph) {
  Backup-File $testGraph $backupDir
  $content = Get-Content $testGraph -Raw
  if ($content -match "from pathlib import Path,\s*re") {
    Write-Host "[PACK] Fixing bad import in $testGraph"
    $new = $content -replace "from pathlib import Path,\s*re", "from pathlib import Path`r`nimport re"
    Set-Content -Encoding UTF8 -Path $testGraph -Value $new
  } else {
    Write-Host "[PACK] $testGraph import already OK"
  }
} else { Write-Host "[PACK] $testGraph not found — skipping" }

# ---- Remove payload\tests to prevent pytest dup import collisions ----
$payloadTests = Join-Path 'payload' 'tests'
if (Test-Path $payloadTests) {
  Write-Host "[PACK] Backing up and removing $payloadTests"
  $dest = Join-Path $backupDir 'payload_tests_backup'
  Copy-Item -Recurse -Force -Path $payloadTests -Destination $dest
  Remove-Item -Recurse -Force -Path $payloadTests
} else { Write-Host "[PACK] No payload\tests dir — OK" }

# ---- Ensure pytest.ini excludes noisy dirs ----
$pytestIni = "pytest.ini"
$pytestBody = @"
[pytest]
norecursedirs = payload .venv tmp _staging _packs _staging_* _packs_* build dist
"@
if (-not (Test-Path $pytestIni)) {
  Write-Host "[PACK] Writing pytest.ini"
  Set-Content -Encoding UTF8 -Path $pytestIni -Value $pytestBody
  Backup-File $pytestIni $backupDir
} else {
  $cur = Get-Content $pytestIni -Raw
  if ($cur -notmatch "norecursedirs") {
    $cur = $cur + "`r`n" + $pytestBody
    Set-Content -Encoding UTF8 -Path $pytestIni -Value $cur
    Backup-File $pytestIni $backupDir
    Write-Host "[PACK] Appended norecursedirs to existing pytest.ini"
  } else {
    Write-Host "[PACK] pytest.ini present"
  }
}

# ---- Clear py caches ----
Write-Host "[PACK] Clearing __pycache__ and *.pyc"
Get-ChildItem -Recurse -Force -Filter "__pycache__" -ErrorAction SilentlyContinue | ForEach-Object { Remove-Item -Recurse -Force -Path $_.FullName -ErrorAction SilentlyContinue }
Get-ChildItem -Recurse -Force -Include *.pyc -ErrorAction SilentlyContinue | ForEach-Object { Remove-Item -Force -Path $_.FullName -ErrorAction SilentlyContinue }

# ---- Patch repo scripts\apply_pack.ps1 to skip same-path copies (defensive) ----
$repoApply = 'scripts\apply_pack.ps1'
if (Test-Path $repoApply) {
  Backup-File $repoApply $backupDir
  $txt = Get-Content $repoApply -Raw
  if ($txt -notmatch 'begin injected skip-if-same-path') {
    $needle = 'Copy-Item -Force -Path $from -Destination $to'
    $idx = $txt.IndexOf($needle)
    if ($idx -ge 0) {
      Write-Host "[PACK] Inserting same-path guard into repo $repoApply"
$guard = @'
# --- begin injected skip-if-same-path ---
try {
  $rpFrom = Resolve-Path $from -ErrorAction Stop
  $rpTo   = Resolve-Path $to   -ErrorAction Stop
} catch {
  Copy-Item -Force -Path $from -Destination $to
  return
}
if ($rpFrom -ieq $rpTo) {
  Write-Host "Skip copy (same path): $rpTo"
} else {
  Copy-Item -Force -Path $from -Destination $to
}
# --- end injected skip-if-same-path ---
'@
      $before = $txt.Substring(0,$idx)
      $after  = $txt.Substring($idx + $needle.Length)
      $txt = $before + $guard + $after
      Set-Content -Encoding UTF8 -Path $repoApply -Value $txt
    } else { Write-Host "[PACK] No Copy-Item pattern found in $repoApply — skip" }
  } else {
    Write-Host "[PACK] Guard already present — skip patch"
  }
} else { Write-Host "[PACK] $repoApply not found — skip" }

# ---- Fix install_cloudflared.ps1 param name clash ($Host -> $BindHost) ----
$inst = 'tools\ps1\install_cloudflared.ps1'
if (Test-Path $inst) {
  Backup-File $inst $backupDir
  $s = Get-Content $inst -Raw
  if ($s -match 'param\([^)]*\$Host\b') {
    Write-Host "[PACK] Renaming param `$Host -> `$BindHost in install_cloudflared.ps1"
    $s = $s -replace '\$Host\b', '$BindHost'
    Set-Content -Encoding UTF8 -Path $inst -Value $s
  } else { Write-Host "[PACK] No `$Host param in $inst — OK" }
} else { Write-Host "[PACK] $inst not found — skip" }

# ---- Run smokes ----
$pytestLog = "tmp\logs\pytest_smoke_$ts.txt"
Write-Host "[PACK] Running pytest -q -m smoke"
try {
  & python -m pytest -q -m smoke *>&1 | Tee-Object -FilePath $pytestLog
} catch {
  Write-Warning "[PACK] pytest exited with error code; see $pytestLog"
}

# ---- Try to start server and tunnel (best-effort) ----
try {
  $tcp = Get-NetTCPConnection -LocalPort 8776 -ErrorAction SilentlyContinue
} catch { $tcp = $null }
if (-not $tcp) {
  $server = 'tools\ps1\run_control_server_lan.ps1'
  if (Test-Path $server) {
    Write-Host "[PACK] Starting LAN control server (detached)"
    Start-Process pwsh -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-File', $server -WindowStyle Minimized
    Start-Sleep -Seconds 2
  }
}

$install = 'tools\ps1\install_cloudflared.ps1'
$tunnel  = 'tools\ps1\run_quick_tunnel.ps1'
if (Test-Path $install) {
  Write-Host "[PACK] Running install_cloudflared.ps1"
  try { pwsh -NoProfile -ExecutionPolicy Bypass -File $install } catch { Write-Warning $_ }
}
if (Test-Path $tunnel) {
  Write-Host "[PACK] Running run_quick_tunnel.ps1"
  try { pwsh -NoProfile -ExecutionPolicy Bypass -File $tunnel } catch { Write-Warning $_ }
}

# Report tunnel URL
$tunnelFile = 'reports\ops\tunnel_url.txt'
if (Test-Path $tunnelFile) {
  Write-Host "[PACK] Tunnel URL file:"
  Get-Content $tunnelFile | ForEach-Object { Write-Host ("    " + $_) }
} else {
  Write-Host "[PACK] No tunnel_url.txt yet"
}

# API check
try {
  $api = Invoke-RestMethod -Uri http://127.0.0.1:8776/api/tunnel -Method Get -TimeoutSec 5
  Write-Host "[PACK] /api/tunnel:"
  $api | ConvertTo-Json -Depth 4 | Write-Host
} catch {
  Write-Host "[PACK] /api/tunnel unavailable"
}

# ---- Git commit (no push) ----
Write-Host "[PACK] Committing changes"
try {
  git add -A
  git commit -m "PA-361: fix smokes, pytest discovery, apply_pack guard, tunnel bring-up hooks" | Out-Null
  Write-Host "[PACK] Commit created (or nothing to commit)"
} catch {
  Write-Host "[PACK] Git commit failed (possibly no changes)"
}

Pop-Location
Write-Host "[PACK] Complete."
