$repo = Split-Path -Parent $PSScriptRoot; $repo = Split-Path -Parent $repo
$logDir = Join-Path $repo "reports\tunnel"
$urlFile = Join-Path $logDir "public_url.txt"
$outFile = Join-Path $logDir "cloudflared.out.log"
$errFile = Join-Path $logDir "cloudflared.err.log"
if (-not (Test-Path $urlFile)) {
  Write-Error "public_url.txt not found. Run scripts\tunnel\run_cloudflared_quick.ps1 first."
  if (Test-Path $outFile){ Get-Content $outFile -Tail 80 }
  if (Test-Path $errFile){ Get-Content $errFile -Tail 80 }
  exit 2
}
$u = Get-Content $urlFile -TotalCount 1
if (-not $u) {
  Write-Error "No URL in public_url.txt"
  if (Test-Path $outFile){ Get-Content $outFile -Tail 80 }
  if (Test-Path $errFile){ Get-Content $errFile -Tail 80 }
  exit 2
}
try {
  $code = (Invoke-WebRequest ($u + "/health") -UseBasicParsing | Select-Object -Expand StatusCode)
  if ($code -ne 200) {
    Write-Error "tunnel health failed, status $code"
    if (Test-Path $outFile){ Get-Content $outFile -Tail 120 }
    if (Test-Path $errFile){ Get-Content $errFile -Tail 120 }
    exit 3
  }
  Write-Output "[OK] tunnel health OK via $u"
} catch {
  Write-Error "tunnel /health request failed: $($_.Exception.Message)"
  if (Test-Path $outFile){ Get-Content $outFile -Tail 200 }
  if (Test-Path $errFile){ Get-Content $errFile -Tail 200 }
  exit 4
}
