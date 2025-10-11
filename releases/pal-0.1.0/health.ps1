param(
  [string]$Url = "http://127.0.0.1:8787/healthz",
  [int]$TimeoutSec = 20
)
$sw = [System.Diagnostics.Stopwatch]::StartNew()
while ($sw.Elapsed.TotalSeconds -lt $TimeoutSec) {
  try {
    $r = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 5
    if ($r.StatusCode -eq 200) { Write-Host "HEALTH OK"; exit 0 }
  } catch { Start-Sleep -Milliseconds 500 }
}
Write-Error "HEALTH FAIL"
exit 2
