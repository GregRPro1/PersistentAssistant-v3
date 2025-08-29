Set-StrictMode -Version Latest

function Trunc-Text { param([string]$Text,[int]$Max=200) if ($null -eq $Text) { return '' } $s=$Text; if ($s.Length -gt $Max) { $s = $s.Substring(0,$Max) } return $s }

function Probe-Urls { param([string[]]$Urls,[int]$TimeoutSec=3)
  $list = @()
  foreach ($u in $Urls) {
    $ok = $false; $code = 0; $err = ''; $body = ''; $start = Get-Date
    try { $resp = Invoke-WebRequest -UseBasicParsing -Uri $u -TimeoutSec $TimeoutSec -ErrorAction Stop; $code = $resp.StatusCode; $ok = $true; $body = Trunc-Text -Text ($resp.Content) -Max 200 }
    catch { $err = Trunc-Text -Text ($_.Exception.Message) -Max 200 }
    $elapsed = [int]((Get-Date) - $start).TotalMilliseconds
    $list += [pscustomobject]@{ url=$u; ok=$ok; status=$code; elapsed_ms=$elapsed; error=$err; body=$body }
  }
  return $list
}

function Probe-AgentEndpoints { param([int]$Port,[int]$TimeoutSec=3)
  $names = @('agent_routes','agent_plan','agent_summary','agent_recent','agent_ac','agent_ws','agent_next2','agent_ui')
  $urls = @()
  foreach ($n in $names) { $urls += ('http://127.0.0.1:' + $Port + '/' + $n) }
  $res = Probe-Urls -Urls $urls -TimeoutSec $TimeoutSec
  $out = @()
  for ($i=0; $i -lt $res.Count; $i++) {
    $out += [pscustomobject]@{ name=$names[$i]; port=$Port; ok=$res[$i].ok; status=$res[$i].status; elapsed_ms=$res[$i].elapsed_ms; error=$res[$i].error; body=$res[$i].body; url=$res[$i].url }
  }
  return $out
}

function Run-AutoHealth {
  $res = [ordered]@{ obj=$null; path=''; error='' }
  try {
    if (-not (Test-Path -LiteralPath '.\tools\auto_health.ps1')) { throw 'tools\\auto_health.ps1 not found' }
    $stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
    $target = Join-Path (Get-Location).Path ('tmp\\run\\auto_health_' + $stamp + '.json')
    try { & '.\tools\auto_health.ps1' -JsonOut $target | Out-Null } catch { try { & '.\tools\auto_health.ps1' | Out-Null } catch {} }
    if (-not (Test-Path -LiteralPath $target)) { $latest = (Get-ChildItem -Path 'tmp\\run\\auto_health_*.json' -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1); if ($latest) { $target = $latest.FullName } }
    if (-not (Test-Path -LiteralPath $target)) { throw 'No auto_health json produced.' }
    $obj = Get-Content -LiteralPath $target -Raw | ConvertFrom-Json
    $res.obj = $obj; $res.path = $target
  } catch { $res.error = $_.Exception.Message }
  return $res
}

function Extract-EndpointResults { param([object]$AutoHealthObj)
  if ($AutoHealthObj -and $AutoHealthObj.PSObject.Properties.Name -contains 'results') { return @(@( $AutoHealthObj.results )) }
  if ($AutoHealthObj -and $AutoHealthObj.PSObject.Properties.Name -contains 'endpoints') { return @(@( $AutoHealthObj.endpoints )) }
  return @()
}

function Print-Endpoints { param([object[]]$Results)
  $arr = @(@( $Results ))
  foreach ($r in $arr) {
    $name = '' + $r.name; $okFlag = $false; if ($r.PSObject.Properties.Name -contains 'ok') { $okFlag = [bool]$r.ok }
    $state = if ($okFlag) { 'OK' } else { 'FAIL' }
    Write-Host ('ENDPOINT {0}: {1}' -f $name, $state)
  }
}

