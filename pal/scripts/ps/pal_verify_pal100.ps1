param([string]$Version = "pal-0.1.0",[string]$HealthUrl = "http://127.0.0.1:8787/healthz",[int]$TimeoutSec = 20)
$errors=@()
$relPath = Join-Path ".\releases" $Version
if (-not (Test-Path $relPath)) { $errors += "Missing release folder: $relPath" }
try { $target = (Get-Item .\current -ErrorAction Stop).Target; if ($null -eq $target -or -not ($target -like "*$Version*")) { $errors += "current does not point to $Version (target: $target)" } }
catch { $errors += "Missing or invalid 'current' junction" }
if (-not (Test-Path ".\current\run.ps1")) { $errors += "Missing .\current\run.ps1" }
$sw=[Diagnostics.Stopwatch]::StartNew(); $ok=$false
while ($sw.Elapsed.TotalSeconds -lt $TimeoutSec) { try { $r=Invoke-WebRequest -Uri $HealthUrl -TimeoutSec 5; if ($r.StatusCode -eq 200) { $ok=$true; break } } catch { Start-Sleep -Milliseconds 500 } }
if (-not $ok) { $errors += "Health check failed: $HealthUrl" }
if ($errors.Count -eq 0) { Write-Host "PAL-100 DoD PASSED" -ForegroundColor Green; exit 0 } else { Write-Host "PAL-100 DoD FAILED:" -ForegroundColor Red; $errors | % { Write-Host " - $_" -ForegroundColor Red }; exit 2 }
