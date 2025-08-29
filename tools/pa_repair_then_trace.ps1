# PA repair+trace (tiny): sanitize Python -> compile -> import wrapper -> maybe start agent -> probe endpoints
# ID: PA_20250827-repair-trace-v1
[CmdletBinding()]
param(
  [Parameter()][string]$BindHost='127.0.0.1',
  [Parameter()][ValidateRange(1,65535)][int]$Port=8782
)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'

function Arr { param($x) if ($null -eq $x) { @() } else { @($x) } }
function Ensure-Dir { param([string]$p) if (-not (Test-Path -LiteralPath $p)) { New-Item -ItemType Directory -Path $p | Out-Null } }

$repo=(Get-Location).Path
Ensure-Dir "tmp"; Ensure-Dir "tmp\run"; Ensure-Dir "tmp\logs"; Ensure-Dir "tmp\feedback"
$ts=Get-Date -Format 'yyyyMMdd_HHmmss'
$repairJson=Join-Path $repo ("tmp\run\repair_server_{0}.json" -f $ts)

# 1) Python sanitize/repair/compile/import
& python ".\tools\py\repair_server_syntax.py" --root . --out $repairJson
$rep = Get-Content -LiteralPath $repairJson -Raw | ConvertFrom-Json
$bad = @($rep.results | Where-Object { -not $_.ok })
if ($bad.Count -gt 0) {
  Write-Host "PY COMPILE ERRORS:"
  foreach ($r in $bad) {
    Write-Host (" - " + $r.file)
    if (''+$r.err) { Write-Host ("   " + ((''+$r.err) -replace "`r","" -replace "`n","  ")) }
  }
}

# 2) If no listener and wrapper imported OK+has_app, start the agent in background
$net = netstat -ano | Select-String -SimpleMatch (":" + $Port)
$pidList = @()
foreach ($ln in Arr $net) {
  $txt = ''+$ln
  if ($txt -match 'LISTENING\s+(\d+)\s*$') {
    try { $pidList += [int]$matches[1] } catch {}
  }
}
$pidList = @($pidList | Sort-Object -Unique)

if ((@($pidList).Count -eq 0) -and $rep.wrapper.ok -and $rep.wrapper.has_app) {
  $env:PA_SIDECAR_HOST=$BindHost
  $env:PA_SIDECAR_PORT="$Port"
  $py="server\agent_sidecar_wrapper.py"
  $out=Join-Path $repo ("tmp\logs\sidecar_{0}.out.log" -f $ts)
  $err=Join-Path $repo ("tmp\logs\sidecar_{0}.err.log" -f $ts)
  try {
    Start-Job -ScriptBlock {
      param($py,$cwd,$o,$e,$h,$p)
      try {
        $env:PA_SIDECAR_HOST=$h; $env:PA_SIDECAR_PORT=""+$p
        Set-Location -Path $cwd
        & python $py 1>> $o 2>> $e
      } catch {
        Add-Content -LiteralPath $e -Value ($_.Exception.GetType().FullName + ": " + $_.Exception.Message)
      }
    } -ArgumentList $py,$repo,$out,$err,$BindHost,$Port | Out-Null
    Start-Sleep -Seconds 2
  } catch {
    Write-Host ("START ERROR: " + $_.Exception.Message)
  }
}

# 3) Probe core endpoints (no Start-Process)
function Probe { param([string]$u,[int]$t=4)
  $rec=[ordered]@{ url=$u; ok=$false; code=0; ms=0; err=""; body="" }
  $t0=Get-Date
  try {
    $r=Invoke-WebRequest -UseBasicParsing -Uri $u -TimeoutSec $t -ErrorAction Stop
    $rec.ok=$true; $rec.code=[int]$r.StatusCode
    $rec.ms=[int]((Get-Date)-$t0).TotalMilliseconds
    $b=''+$r.Content; if ($b.Length -gt 160) { $b=$b.Substring(0,160) }
    $rec.body=($b -replace "`r"," " -replace "`n"," ")
  } catch {
    $rec.ok=$false; $rec.ms=[int]((Get-Date)-$t0).TotalMilliseconds
    $rec.err=$_.Exception.GetType().FullName + ": " + $_.Exception.Message
    if ($_.Exception.Response -and $_.Exception.Response.StatusCode) {
      try { $rec.code=[int]$_.Exception.Response.StatusCode } catch {}
    }
  }
  return [pscustomobject]$rec
}

$base="http://$($BindHost):$($Port)"
$targets=@("/health","/__routes__","/agent/_sig","/agent/plan","/agent/recent","/agent/next2")
$probes=New-Object System.Collections.Generic.List[object]
foreach ($p in $targets) {
  $res=Probe -u ($base+$p)
  $probes.Add($res)
  $st = "FAIL"; if ($res.ok) { $st="OK" }
  Write-Host ($st + " " + $p + " code=" + $res.code + " ms=" + $res.ms)
  if (-not $res.ok -and $res.err) { Write-Host ("  err: " + $res.err) }
  if ($res.ok -and $res.body) { Write-Host ("  body: " + $res.body) }
}

# 4) Final status + footer
$healthOk = ($probes | Where-Object { $_.url -eq ($base+"/health") -and $_.ok }).Count -gt 0
$status = "OK"
if ($bad.Count -gt 0) { $status = "FAIL agent_compile_error" }
elseif (-not $healthOk) { $status = "FAIL agent_not_responding" }

# Minimal pack
$stage = Join-Path $repo ("tmp\feedback\pack_repair_trace_{0}.staging" -f $ts)
$zip   = Join-Path $repo ("tmp\feedback\pack_repair_trace_{0}.zip" -f $ts)
Ensure-Dir $stage
Copy-Item -LiteralPath $repairJson -Destination (Join-Path $stage "repair_server_syntax.json") -Force
($probes | ConvertTo-Json -Depth 6) | Set-Content -LiteralPath (Join-Path $stage "probes.json") -Encoding UTF8
$tailOut = Get-ChildItem -Path "tmp\logs" -Filter "sidecar_*.out.log" -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1
$tailErr = Get-ChildItem -Path "tmp\logs" -Filter "sidecar_*.err.log" -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if ($tailOut) { Copy-Item -LiteralPath $tailOut.FullName -Destination (Join-Path $stage "tail_sidecar_out.log") -Force }
if ($tailErr) { Copy-Item -LiteralPath $tailErr.FullName -Destination (Join-Path $stage "tail_sidecar_err.log") -Force }
if (Test-Path -LiteralPath "project\plans\project_plan_v3.yaml") { Copy-Item -LiteralPath "project\plans\project_plan_v3.yaml" -Destination (Join-Path $stage "plan_snapshot.yaml") -Force }
if (Test-Path -LiteralPath $zip) { Remove-Item -LiteralPath $zip -Force }
Compress-Archive -Path (Join-Path $stage '*') -DestinationPath $zip -Force
$absZip=(Resolve-Path -LiteralPath $zip).Path

Write-Host ("PACK: " + $absZip)
Write-Host ("STATUS: " + $status)
Write-Host "python ./tools/show_next_step.py"
