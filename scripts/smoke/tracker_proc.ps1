# tracker_proc.ps1 — confirm tracker wrapper is what starts
Get-Process -Name python -ErrorAction SilentlyContinue | ForEach-Object {
  try { Write-Host ([string]::Join(' ', .Path, .Id)) } catch {}
}
Write-Host "
Likely wrapper path from settings:"
try {
  \ = Get-Content -LiteralPath (Join-Path (git rev-parse --show-toplevel 2>$null) 'config\pal_settings.yaml') -Raw
  (\ -split "
") | Where-Object { \ -match 'tracker_script' } | Write-Host
} catch {}
