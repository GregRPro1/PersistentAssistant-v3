Param()
$ErrorActionPreference = 'Stop'
function Ensure-Dir([string]$p){ if(-not (Test-Path $p)){ New-Item -ItemType Directory -Path $p | Out-Null } }
function Newest([string]$glob){
  $items = Get-ChildItem -Path $glob -ErrorAction SilentlyContinue
  if($items){ ($items | Sort-Object LastWriteTime -Descending)[0] } else { $null }
}
$root = (Get-Location).Path
$tmp  = Join-Path $root "tmp"
$fb   = Join-Path $tmp  "feedback"
$run  = Join-Path $tmp  "run"
Ensure-Dir $tmp; Ensure-Dir $fb; Ensure-Dir $run

$py        = (Test-Path (Join-Path $root ".venv\Scripts\python.exe")) ? (Join-Path $root ".venv\Scripts\python.exe") : "python"
$validator = Join-Path $root "tools\reply_contract\validator.py"
$gate      = Join-Path $root "tools\pa_reply_gate.ps1"
$wire      = Join-Path $root "tests\reply_contract_wiretest.ps1"

# re-run wire test
$wireOut = & powershell -ExecutionPolicy Bypass -File $wire -PyPath $py 2>$null | Out-String

# samples
$okSample  = Newest (Join-Path $run "reply_ok_*.txt")
$badSample = Newest (Join-Path $run "reply_bad_*.txt")
$fixSample = Newest (Join-Path $run "reply_fix_*.txt")

$result = [ordered]@{
  time_utc = (Get-Date).ToUniversalTime().ToString("o")
  ok_gate  = $false; bad_gate = $false; fix_gate = $false
  ok_path  = $null;  bad_path = $null;  fix_path = $null
  wire_out = $wireOut
}

if($okSample){
  Copy-Item $okSample.FullName (Join-Path $tmp "assistant_reply.txt") -Force
  & powershell -ExecutionPolicy Bypass -File $gate -ReplyPath (Join-Path $tmp "assistant_reply.txt") | Out-Null
  $result.ok_gate = ($LASTEXITCODE -eq 0); $result.ok_path = (Join-Path $tmp "assistant_reply.txt")
}
if($badSample){
  Copy-Item $badSample.FullName (Join-Path $tmp "assistant_reply.txt") -Force
  & powershell -ExecutionPolicy Bypass -File $gate -ReplyPath (Join-Path $tmp "assistant_reply.txt") | Out-Null
  $result.bad_gate = ($LASTEXITCODE -eq 0); $result.bad_path = (Join-Path $tmp "assistant_reply.txt")
}
if($fixSample){
  Copy-Item $fixSample.FullName (Join-Path $tmp "assistant_reply.txt") -Force
  & powershell -ExecutionPolicy Bypass -File $gate -ReplyPath (Join-Path $tmp "assistant_reply.txt") | Out-Null
  $result.fix_gate = ($LASTEXITCODE -eq 0); $result.fix_path = (Join-Path $tmp "assistant_reply.txt")
}

$ts = Get-Date -Format "yyyyMMdd_HHmmss"
$sum = Join-Path $fb ("reply_contract_e2e_{0}.json" -f $ts)
$result | ConvertTo-Json -Depth 6 | Set-Content $sum -Encoding UTF8
"OUT: $sum"
