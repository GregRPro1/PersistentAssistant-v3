param(
  [string]$Version = "pal-0.1.0",
  [string]$HealthUrl = "http://127.0.0.1:8787/healthz",
  [string]$TaskId = "PAL-100"
)
$ok = $false
try { pwsh .\current\health.ps1 -Url $HealthUrl -TimeoutSec 20 | Out-Null; $ok = $true } catch { $ok = $false }
if (-not $ok) { Write-Error "PAL-100 verification failed (health)."; exit 2 }
$python = "$env:VIRTUAL_ENV\Scripts\python.exe"; if (-not (Test-Path $python)) { $python = "python" }
& $python ".\pal\scripts\py\pal_mark_done.py" $TaskId
if ($LASTEXITCODE -ne 0) { Write-Error "Failed to mark $TaskId as done."; exit 2 }
$reqDir = ".\pal\control\requests"; if (-not (Test-Path $reqDir)) { New-Item -ItemType Directory -Force -Path $reqDir | Out-Null }
$reqPath = Join-Path $reqDir ("{0}.json" -f (Get-Date -Format "yyyyMMdd_HHmmss_fff"))
'{"command":"restart","target":"tracker","note":"refresh after marking done"}' | Set-Content $reqPath -Encoding UTF8
Write-Host "PAL-100 marked done and tracker restart requested."; exit 0
