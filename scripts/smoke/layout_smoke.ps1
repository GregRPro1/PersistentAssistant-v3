
param(
  [int]$Port = $env:WATCHDOG_PORT
)
if (-not $Port) { $Port = 9001 }
$urls = @("http://127.0.0.1:$Port/","http://127.0.0.1:8787/")
$ok = $false
foreach ($u in $urls) {
  try {
    $r = Invoke-WebRequest -UseBasicParsing -Uri $u -TimeoutSec 5
    if ($r.StatusCode -ge 200 -and $r.StatusCode -lt 400) {
      if ($r.Content -match 'PAL-UX-INLINE B.2') { Write-Host "[OK] inline marker present at $u"; $ok=$true; break }
      else { Write-Host "[MISS] inline marker not found at $u" }
    }
  } catch { Write-Host "[ERR] $_" }
}
if (-not $ok) { Write-Error "Layout inject not detected (no PAL-UX marker)."; exit 1 }
Write-Host "Layout smoke passed."
