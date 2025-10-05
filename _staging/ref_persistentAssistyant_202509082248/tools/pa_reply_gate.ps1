Param(
  [string]$ReplyPath = ".\tmp\assistant_reply.txt",
  [switch]$RewriteIfNeeded = $true
)
$ErrorActionPreference = 'Stop'
function Ensure-Dir([string]$p){ if(-not (Test-Path $p)){ New-Item -ItemType Directory -Path $p | Out-Null } }
$root = (Get-Location).Path
$tmp  = Join-Path $root "tmp"
$run  = Join-Path $tmp  "run"
Ensure-Dir $tmp; Ensure-Dir $run
$py = (Test-Path (Join-Path $root ".venv\Scripts\python.exe")) ? (Join-Path $root ".venv\Scripts\python.exe") : "python"
$validator = Join-Path $root "tools\reply_contract\validator.py"

if(-not (Test-Path $ReplyPath)){ "REPLY: missing ($ReplyPath) — not blocking." ; exit 0 }

$null = & $py $validator text $ReplyPath 2>$null
if($LASTEXITCODE -eq 0){ "REPLY: schema OK" ; exit 0 }

"REPLY: schema FAIL — attempting auto-rewrite..."
$fixed = Join-Path $run "assistant_reply_fixed.txt"
$null = & $py $validator rewrite $ReplyPath $fixed 2>$null
$null = & $py $validator text $fixed 2>$null
if($LASTEXITCODE -eq 0){
  if($RewriteIfNeeded){ Copy-Item $fixed $ReplyPath -Force ; "REPLY: auto-rewrite applied → OK" ; exit 0 }
  else { "REPLY: fixed at $fixed (not applied)"; exit 1 }
} else { "REPLY: rewrite failed — see $fixed" ; exit 2 }
