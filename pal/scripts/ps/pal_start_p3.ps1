param([string]$Phase = "P3")
$python = "$env:VIRTUAL_ENV\Scripts\python.exe"; if (-not (Test-Path $python)) { $python = "python" }
& $python ".\pal\scripts\py\pal_phase_tools.py" set $Phase in_progress
$reqDir = ".\pal\control\requests"; if (-not (Test-Path $reqDir)) { New-Item -ItemType Directory -Force -Path $reqDir | Out-Null }
$req = Join-Path $reqDir ("{0}.json" -f (Get-Date -Format "yyyyMMdd_HHmmss_fff"))
'{"command":"restart","target":"tracker","note":"P3 set in_progress"}' | Set-Content $req -Encoding UTF8
