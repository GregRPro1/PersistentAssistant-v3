param(
  [Parameter(Mandatory=$true)][string]$In,
  [string]$Out = $(Join-Path (Split-Path -Parent $In) ((Split-Path -Leaf $In) + ".fixed.ps1")),
  [switch]$Run
)
$py = if(Test-Path ".\.venv\Scripts\python.exe"){ ".\.venv\Scripts\python.exe" } else { "python" }
$parser = "tools\preflight_parser.py"
if(-not(Test-Path $parser)){ Write-Error "missing $parser"; exit 1 }
$res = & $py $parser $In $Out
Write-Host "PREFLIGHT RESULT: $res"
if($Run){
  Write-Host "RUNNING fixed script: $Out"
  & powershell -ExecutionPolicy Bypass -File $Out
}