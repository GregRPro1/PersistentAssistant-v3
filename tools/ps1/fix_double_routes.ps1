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
