param([string]$JsonOut = "")
$ErrorActionPreference = "Stop"

function Save-Content([string]$Path,[string]$Text){
  Set-Content -Path $Path -Value $Text -Encoding UTF8
}

function Invoke-Http([string]$Url, [hashtable]$Headers){
  try{
    if($Headers -and $Headers.Count -gt 0){
      return Invoke-WebRequest -Uri $Url -TimeoutSec 6 -Headers $Headers -UseBasicParsing
    } else {
      return Invoke-WebRequest -Uri $Url -TimeoutSec 6 -UseBasicParsing
    }
  }catch{
    return $null
  }
}

function Get-PhoneToken{
  $p = Join-Path (Get-Location).Path "config\phone_approvals.yaml"
  if(-not (Test-Path $p)){ return "" }
  $tok = ""
  foreach($ln in Get-Content $p){
    $s = $ln.Trim()
    if($s -like "token:*"){
      $val = ($s.Split(":",2)[1]).Trim()
      if($val.StartsWith('"') -and $val.EndsWith('"')){ $val = $val.Substring(1, $val.Length-2) }
      if($val.StartsWith("'") -and $val.EndsWith("'")){ $val = $val.Substring(1, $val.Length-2) }
      $tok = $val; break
    }
  }
  return $tok
}

$agentBase = "http://127.0.0.1:8782"
$phoneBase = "http://127.0.0.1:8781"
$token = Get-PhoneToken
$hdr   = @{}
if($token){ $hdr["Authorization"] = "Bearer " + $token }

$checks = @(
  @{ name="agent_routes"; url=$agentBase + "/__routes__";       headers=@{} },
  @{ name="agent_plan";   url=$agentBase + "/agent/plan";       headers=$hdr },
  @{ name="agent_summary";url=$agentBase + "/agent/summary";    headers=$hdr },
  @{ name="agent_recent"; url=$agentBase + "/agent/recent";     headers=$hdr },
  @{ name="agent_ac";     url=$agentBase + "/agent/approvals_count"; headers=$hdr },
  @{ name="agent_ws";     url=$agentBase + "/agent/worker_status";   headers=$hdr },
  @{ name="agent_next2";  url=$agentBase + "/agent/next2";      headers=$hdr },
  @{ name="agent_ui";     url=$agentBase + "/pwa/agent";        headers=@{} },
  @{ name="phone_routes"; url=$phoneBase + "/__routes__";       headers=@{} },
  @{ name="phone_ping";   url=$phoneBase + "/phone/ping";       headers=@{} },
  @{ name="phone_health"; url=$phoneBase + "/phone/health";     headers=@{} },
  @{ name="phone_cfg";    url=$phoneBase + "/pwa/config";       headers=@{} },
  @{ name="phone_diag";   url=$phoneBase + "/pwa/diag";         headers=@{} }
)

$results = @()
foreach($c in $checks){
  $resp = Invoke-Http $c.url $c.headers
  $ok    = $false
  $status= 0
  $bytes = 0
  if($resp){
    $ok = $true
    $status = [int]$resp.StatusCode
    $bytes  = [int]$resp.RawContentLength
  }
  $results += [pscustomobject]@{ name=$c.name; url=$c.url; ok=$ok; status=$status; bytes=$bytes }
}

$agentOk=0; $agentTotal=0; $phoneOk=0; $phoneTotal=0
foreach($r in $results){
  if($r.name -like "agent_*"){ $agentTotal++; if($r.ok){ $agentOk++ } }
  if($r.name -like "phone_*"){ $phoneTotal++; if($r.ok){ $phoneOk++ } }
}

$sum = [ordered]@{
  time_utc     = (Get-Date).ToUniversalTime().ToString("o")
  token_present= [bool]$token
  agent        = @{ ok=$agentOk; total=$agentTotal }
  phone        = @{ ok=$phoneOk; total=$phoneTotal }
  results      = $results
}

if($JsonOut -and $JsonOut.Length -gt 0){
  Save-Content -Path $JsonOut -Text ($sum | ConvertTo-Json -Depth 6)
}

Write-Host ("AGENT OK: {0}/{1}" -f $agentOk, $agentTotal)
Write-Host ("PHONE OK: {0}/{1}" -f $phoneOk, $phoneTotal)
