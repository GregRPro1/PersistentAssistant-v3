$python = "$env:VIRTUAL_ENV\Scripts\python.exe"; if (-not (Test-Path $python)) { $python = "python" }
& $python ".\pal\scripts\py\pal_add_goalposts.py"
# restart tracker
$reqDir = ".\pal\control\requests"; if (-not (Test-Path $reqDir)) { New-Item -ItemType Directory -Force -Path $reqDir | Out-Null }
$req = Join-Path $reqDir ("{0}.json" -f (Get-Date -Format "yyyyMMdd_HHmmss_fff"))
'{"command":"restart","target":"tracker","note":"goalposts injected"}' | Set-Content $req -Encoding UTF8
Write-Host "Goalposts added; tracker restart requested."
