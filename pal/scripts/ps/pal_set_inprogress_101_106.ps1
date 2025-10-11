$ids = @('PAL-101','PAL-102','PAL-103','PAL-104','PAL-105','PAL-106')
$python = "$env:VIRTUAL_ENV\Scripts\python.exe"; if (-not (Test-Path $python)) { $python = "python" }
& $python ".\pal\scripts\py\pal_mark_status.py" in_progress @ids
# restart tracker to refresh colors
$reqDir = ".\pal\control\requests"; if (-not (Test-Path $reqDir)) { New-Item -ItemType Directory -Force -Path $reqDir | Out-Null }
$req = Join-Path $reqDir ("{0}.json" -f (Get-Date -Format "yyyyMMdd_HHmmss_fff"))
'{"command":"restart","target":"tracker","note":"refresh after marking 101-106 in_progress"}' | Set-Content $req -Encoding UTF8
Write-Host "Marked PAL-101..106 in_progress and requested tracker restart."
