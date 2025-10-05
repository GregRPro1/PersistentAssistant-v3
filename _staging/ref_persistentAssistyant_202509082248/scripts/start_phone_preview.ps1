param([string]$Venv = ".venv")
$ErrorActionPreference = "Stop"
$py = Join-Path $Venv "Scripts\python.exe"
if (!(Test-Path $py)) { $py = "python" }
& $py -m pip install flask pyyaml | Out-Null
& $py tools\phone_preview.py
