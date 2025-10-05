# Apply minimal admin toolset (route de-dup + restart + route map)
# Usage: pwsh -NoProfile -ExecutionPolicy Bypass -File <unzipped>\scripts\apply_pack.ps1

$ErrorActionPreference = 'Stop'

function Write-Note($msg){ Write-Host ("[ADMIN-PACK] " + $msg) }

# 1) Ensure target dir for tools exists
$tools = 'tools\ps1'
if (-not (Test-Path $tools)) { New-Item -ItemType Directory -Force $tools | Out-Null }

# 2) Write the route fix script
$fixPath = Join-Path $tools 'fix_double_routes.ps1'
$fixContent = @'
param([switch]$DryRun)

$ErrorActionPreference = "Stop"

function _Backup($path){
  try {
    $stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
    Copy-Item -LiteralPath $path -Destination ($path + ".bak_" + $stamp) -Force
  } catch {}
}

$files = @(
  'server\watchdog_api.py',
  'server\watchdog_api_fallback.py',
  'server\watchdog_ui.py',
  'server\watchdog_ui_fallback.py'
) | Where-Object { Test-Path $_ }

if (-not $files) {
  Write-Host "No watchdog files found to patch."
  exit 0
}

$changed = @()

foreach($f in $files){
  $orig = Get-Content -LiteralPath $f -Raw

  # Normalize any decorators that include '/api/watchdog' or '/app/watchdog' to '/watchdog' (quotes either ' or ")
  $patched = $orig `
    -replace '(@\s*\w+\.route\()\s*["'']/api/watchdog', '$1"/watchdog' `
    -replace '(@\s*\w+\.route\()\s*["'']/api/watchdog/', '$1"/watchdog/' `
    -replace '(@\s*\w+\.route\()\s*["'']/app/watchdog', '$1"/watchdog' `
    -replace '(@\s*\w+\.route\()\s*["'']/app/watchdog/', '$1"/watchdog/'

  if ($patched -ne $orig) {
    if (-not $DryRun) {
      _Backup $f
      Set-Content -LiteralPath $f -Value $patched -Encoding UTF8
    }
    $changed += $f
  }
}

if ($changed) {
  Write-Host ("Patched files:`n - " + ($changed -join "`n - "))
} else {
  Write-Host "No changes needed; watchdog routes already normalized."
}
'@

Set-Content -LiteralPath $fixPath -Value $fixContent -Encoding UTF8
Write-Note ("Installed helper: {0}" -f $fixPath)

# 3) Run the fix (non-dry)
Write-Note "Normalizing routes in watchdog modules…"
pwsh -NoProfile -ExecutionPolicy Bypass -File $fixPath | Write-Host

# 4) Restart watchdog (best-effort)
Write-Note "Restarting watchdog…"
try { pwsh -NoProfile -ExecutionPolicy Bypass tools\ps1\stop_watchdog.ps1 | Out-Null } catch {}
Start-Sleep -Milliseconds 600
try { pwsh -NoProfile -ExecutionPolicy Bypass tools\ps1\run_watchdog.ps1  | Out-Null } catch {}

# 5) Probe health and route map
Start-Sleep -Seconds 2
$base = "http://127.0.0.1:8776"
function _Try($url){ 
  try { Invoke-WebRequest -UseBasicParsing -TimeoutSec 5 -Uri $url } catch { $null } 
}

$h = _Try "$base/healthz"
if ($h) { Write-Note ("healthz: {0}" -f $h.StatusCode) } else { Write-Note "healthz: unreachable" }

$d = _Try "$base/__debug"
if ($d) { 
  Write-Host "ROUTES:"
  $lines = ($d.Content -split "`r?`n") | Where-Object { $_ -match '^\s*/' }
  $lines | ForEach-Object { $_.Trim() } | ForEach-Object { Write-Host $_ }
} else {
  Write-Note "__debug: unreachable"
}

Write-Note "Done."
