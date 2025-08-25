param(
  [string]$Base = "http://127.0.0.1:8782",
  [string]$PackDir = "tmp\feedback"
)
$ErrorActionPreference='Continue'

function GET-Slim([string]$url){
  try{
    $r = Invoke-WebRequest -Uri $url -TimeoutSec 8 -UseBasicParsing
    return [pscustomobject]@{ ok=$true; status=[int]$r.StatusCode; body=$r.Content; bytes=($r.Content.Length) }
  } catch {
    $code = 0
    try{ $code = [int]$_.Exception.Response.StatusCode.value__ }catch{}
    return [pscustomobject]@{ ok=$false; status=$code; body=''; bytes=0 }
  }
}

$endpoints = @(
  '/agent/summary',
  '/agent/plan',
  '/agent/recent',
  '/agent/next2',
  '/agent/worker_status',
  '/agent/approvals_count'
)

$results = @{}
foreach($e in $endpoints){ $results[$e] = GET-Slim ($Base+$e) }

$agent = GET-Slim "$Base/pwa/agent?cb=$(Get-Random)"
$domBtns=$false; $domPanes=$false
if($agent.ok){
  $html = $agent.body
  $needBtns = @('paBtnSummary','paBtnPlan','paBtnRecent','paBtnNext','paBtnAsk')
  $needPanes = @('paSummary','paPlan','paRecent','paNext','paStatusBar')

  $btnFlags=@()
  foreach($id in $needBtns){ $btnFlags += @([bool]($html -match $id)) }
  $domBtns = -not ($btnFlags -contains $false)

  $paneFlags=@()
  foreach($id in $needPanes){ $paneFlags += @([bool]($html -match $id)) }
  $domPanes = -not ($paneFlags -contains $false)
}

# Plan snapshot (if present)
$planPath=$null; $planText=$null
try{
  $found = Get-ChildItem -Path . -Filter 'project_plan_v3.yaml' -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
  if($found){ $planPath = $found.FullName; $planText = Get-Content -LiteralPath $planPath -Raw -Encoding UTF8 }
}catch{}

# Routes
$routesBody = (GET-Slim "$Base/__routes__").body

$ts = Get-Date -Format 'yyyyMMdd_HHmmss'
$diag = [ordered]@{
  time_utc=(Get-Date).ToUniversalTime().ToString('o')
  base=$Base
  endpoints=($endpoints | ForEach-Object { [pscustomobject]@{ endpoint=$_; ok=$results[$_].ok; status=$results[$_].status; bytes=$results[$_].bytes } })
  dom_buttons=$domBtns
  dom_panes=$domPanes
  routes=$routesBody
  plan_path=$planPath
}
$json = Join-Path $PackDir ("agent_ui_wiretest_full_{0}.json" -f $ts)
$diag | ConvertTo-Json -Depth 6 | Set-Content $json -Encoding UTF8

# Write plan snapshot alongside
if($planPath -and $planText){
  $planSnap = Join-Path $PackDir ("plan_snapshot_{0}.yaml" -f $ts)
  Set-Content -LiteralPath $planSnap -Value $planText -Encoding UTF8
}

# Pack
$zip="$json.zip"; if(Test-Path $zip){ Remove-Item $zip -Force }
$toPack=@($json)
if($planPath -and $planText){ $toPack += @(Join-Path $PackDir ("plan_snapshot_{0}.yaml" -f $ts)) }
Compress-Archive -Path $toPack -DestinationPath $zip -Force
"PACK: $((Resolve-Path $zip).Path)"
"STATUS: OK (UI wiretest full — endpoints + DOM + plan snapshot)"