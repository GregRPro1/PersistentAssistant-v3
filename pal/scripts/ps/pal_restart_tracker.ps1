$reqDir = ".\pal\control\requests"
if (-not (Test-Path $reqDir)) { New-Item -ItemType Directory -Force -Path $reqDir | Out-Null }
$reqPath = Join-Path $reqDir ("{0}.json" -f (Get-Date -Format "yyyyMMdd_HHmmss_fff"))
'{"command":"restart","target":"tracker"}' | Set-Content $reqPath -Encoding UTF8
Write-Host "Tracker restart request enqueued: $reqPath"
