Param([string]$PyPath="")
$ErrorActionPreference='Stop'
function Ensure-Dir($p){ if(-not (Test-Path $p)){ New-Item -ItemType Directory -Path $p | Out-Null } }
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$root = Split-Path -Parent $here
$tmp  = Join-Path $root "tmp"; $fb = Join-Path $tmp "feedback"; $run = Join-Path $tmp "run"
Ensure-Dir $tmp; Ensure-Dir $fb; Ensure-Dir $run
$py = if([string]::IsNullOrWhiteSpace($PyPath)){ "python" } else { $PyPath }
$validator = Join-Path $root "tools\\reply_contract\\validator.py"

$ts = Get-Date -Format "yyyyMMdd_HHmmss"
$okTxt = Join-Path $run ("reply_ok_{0}.txt" -f $ts)
$badTxt= Join-Path $run ("reply_bad_{0}.txt" -f $ts)
$fixTxt= Join-Path $run ("reply_fix_{0}.txt" -f $ts)
$sumJs = Join-Path $fb  ("reply_contract_wiretest_{0}.json" -f $ts)

# OK sample
& $py $validator sample $okTxt 2>$null

# BAD sample
@"
this is free-form text
without schema headers
it should be rewritten
"@ | Set-Content -Path $badTxt -Encoding UTF8

# Validate
$okJson  = & $py $validator text $okTxt  2>$null; $okPass  = ($LASTEXITCODE -eq 0)
$badJson = & $py $validator text $badTxt 2>$null; $badPass = ($LASTEXITCODE -eq 0)
& $py $validator rewrite $badTxt $fixTxt 2>$null
$fixJson = & $py $validator text $fixTxt 2>$null; $fixPass = ($LASTEXITCODE -eq 0)

# Summary
$summary = [ordered]@{
  time_utc = (Get-Date).ToUniversalTime().ToString("o")
  ok_text_path = $okTxt; bad_text_path = $badTxt; fix_text_path = $fixTxt
  validate_ok_pass = $okPass; validate_bad_pass = $badPass; validate_fix_pass = $fixPass
  validate_ok_json = $okJson;  validate_bad_json = $badJson;  validate_fix_json = $fixJson
}
$summary | ConvertTo-Json -Depth 6 | Set-Content $sumJs -Encoding UTF8

"RESULT: ok=$okPass bad=$badPass fix=$fixPass"
"OUT: $sumJs"
