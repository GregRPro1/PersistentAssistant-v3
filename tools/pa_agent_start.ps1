# Persistent Assistant — Start/Verify Agent Sidecar (robust, minimal, with parser precheck)
# ID: PA_20250827-agent-start-v2.3
# Platform: Windows + PowerShell (ASCII only)
# Rules: Non-interactive; idempotent; check-before-write; never block STDIN

[CmdletBinding()]
param(
  [Parameter()][string]$BindHost = '127.0.0.1',
  [Parameter()][ValidateRange(1,65535)][int]$Port = 8782,
  [Parameter()][ValidateSet('quiet','normal','verbose')][string]$Verbosity = 'normal',
  [Parameter()][int]$StartupTimeoutSec = 25
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Log { param([string]$Level,[string]$Msg)
  $map = @{ quiet=0; normal=1; verbose=2 }
  $cur = 1
  if ($map.ContainsKey($Verbosity)) { $cur = $map[$Verbosity] }
  $need = 1
  if ($Level -eq 'quiet') { $need = 0 }
  if ($Level -eq 'verbose') { $need = 2 }
  if ($cur -ge $need) {
    $ts = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
    Write-Host ("[{0}] {1}" -f $ts, $Msg)
  }
}

function Ensure-Dir { param([string]$Path) if (-not (Test-Path -LiteralPath $Path)) { New-Item -ItemType Directory -Path $Path | Out-Null } }

function Get-PidsOnPort { param([int]$ListenPort)
  $pids = @()
  try {
    $lines = netstat -ano | Select-String -SimpleMatch (":$ListenPort")
    foreach ($ln in $lines) {
      $txt = '' + $ln
      if ($txt -match 'LISTENING\s+(\d+)\s*$') {
        $pidNum = [int]$matches[1]
        if ($pidNum -gt 0) { $pids += $pidNum }
      }
    }
  } catch {}
  $pids = $pids | Sort-Object -Unique
  return $pids
}

function Stop-Pids { param([int[]]$PidList)
  foreach ($pidNum in $PidList) {
    try {
      $proc = Get-Process -Id $pidNum -ErrorAction SilentlyContinue
      if ($null -ne $proc) {
        Stop-Process -Id $pidNum -Force -ErrorAction SilentlyContinue
        Log normal ("Stopped PID {0}" -f $pidNum)
      }
    } catch {}
  }
}

function Test-Url { param([string]$Url,[int]$TimeoutSec=3)
  try {
    $req = Invoke-WebRequest -Uri $Url -TimeoutSec $TimeoutSec -UseBasicParsing -Method GET -ErrorAction Stop
    if ($req.StatusCode -ge 200 -and $req.StatusCode -lt 300) { return $true }
  } catch {}
  return $false
}

# -----------------------------------------------------------------------------
# 0) Parser precheck (best-effort). If tools\ps\Test-PSScripts.ps1 exists and finds errors, fail fast.
# -----------------------------------------------------------------------------
try {
  $gate = ".\tools\ps\Test-PSScripts.ps1"
  if (Test-Path -LiteralPath $gate) {
    # Write JSON to tmp\run but ignore output on success.
    Ensure-Dir "tmp"; Ensure-Dir "tmp\run"
    $tmpJson = Join-Path (Get-Location).Path ("tmp\run\ps_parse_{0}.json" -f (Get-Date -Format 'yyyyMMdd_HHmmss'))
    & $gate -Root (Resolve-Path ".").Path -JsonOut $tmpJson | Out-Null
  }
} catch {
  Write-Host "PACK: [NOT CREATED]"
  Write-Host "STATUS: FAIL ps_parse_errors"
  Write-Host "python ./tools/show_next_step.py"
  exit 10
}

# -----------------------------------------------------------------------------
# 1) Prepare paths, logs, environment
# -----------------------------------------------------------------------------
$repoRoot = (Get-Location).Path
Ensure-Dir "tmp"; Ensure-Dir "tmp\logs"; Ensure-Dir "tmp\run"
$stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$logOut = Join-Path $repoRoot ("tmp\logs\sidecar_{0}.out.log" -f $stamp)
$logErr = Join-Path $repoRoot ("tmp\logs\sidecar_{0}.err.log" -f $stamp)
$healthJson = Join-Path $repoRoot ("tmp\run\auto_health_{0}.json" -f $stamp)

# -----------------------------------------------------------------------------
# 2) Clear stale listener (if any) on the target port
# -----------------------------------------------------------------------------
$pids = Get-PidsOnPort -ListenPort $Port
if ($pids.Count -gt 0) {
  Log normal ("Port {0} is busy; stopping {1} process(es)..." -f $Port, $pids.Count)
  Stop-Pids -PidList $pids
  Start-Sleep -Seconds 1
}

# -----------------------------------------------------------------------------
# 3) Start the agent sidecar in background
# -----------------------------------------------------------------------------
$env:PA_SIDECAR_HOST = $BindHost
$env:PA_SIDECAR_PORT = "$Port"

$pyPath = Join-Path $repoRoot "server\agent_sidecar_wrapper.py"
if (-not (Test-Path -LiteralPath $pyPath)) {
  Write-Host "PACK: [NOT CREATED]"
  Write-Host "STATUS: FAIL agent_wrapper_missing"
  Write-Host "python ./tools/show_next_step.py"
  exit 1
}

$startInfo = @{
  FilePath               = "python"
  ArgumentList           = @($pyPath)
  WorkingDirectory       = $repoRoot
  NoNewWindow            = $true
  PassThru               = $true
  RedirectStandardOutput = $logOut
  RedirectStandardError  = $logErr
}
try {
  $proc = Start-Process @startInfo
  Log normal ("Launched agent wrapper as PID {0}" -f $proc.Id)
} catch {
  Write-Host "PACK: [NOT CREATED]"
  Write-Host "STATUS: FAIL agent_start_failed"
  Write-Host "python ./tools/show_next_step.py"
  exit 2
}

# -----------------------------------------------------------------------------
# 4) Poll health until up or timeout
# -----------------------------------------------------------------------------
$healthUrl = "http://$($BindHost):$($Port)/health"
$deadline = (Get-Date).AddSeconds($StartupTimeoutSec)
$up = $false
do {
  if (Test-Url -Url $healthUrl -TimeoutSec 2) { $up = $true; break }
  Start-Sleep -Milliseconds 400
} while ((Get-Date) -lt $deadline)

# -----------------------------------------------------------------------------
# 5) Run auto_health and print endpoint statuses
# -----------------------------------------------------------------------------
$healthObj = $null
$healthErr = $null
try {
  if (Test-Path -LiteralPath ".\tools\auto_health.ps1") {
    & ".\tools\auto_health.ps1" -JsonOut $healthJson | Out-Null
    if (Test-Path -LiteralPath $healthJson) {
      $healthObj = Get-Content -LiteralPath $healthJson -Raw | ConvertFrom-Json
    }
  } else {
    $healthErr = "tools\auto_health.ps1 not found"
  }
} catch { $healthErr = $_.Exception.Message }

function Print-Endpoints { param([object]$Obj)
  if ($null -eq $Obj) { return }
  $eps = @()
  if ($Obj.PSObject.Properties.Name -contains 'results'   -and $Obj.results)   { $eps = @($Obj.results) }
  elseif ($Obj.PSObject.Properties.Name -contains 'endpoints' -and $Obj.endpoints) { $eps = @($Obj.endpoints) }
  foreach ($e in $eps) {
    $name = '' + $e.name
    $state = 'FAIL'
    if ($e.PSObject.Properties.Name -contains 'ok') {
      if ([bool]$e.ok) { $state = 'OK' }
    }
    Write-Host ("ENDPOINT {0}: {1}" -f $name, $state)
  }
}

if ($healthObj -ne $null) {
  $agentOk = 0; $agentTotal = 0; $phoneOk = 0; $phoneTotal = 0
  $eps = @()
  if ($healthObj.results) { $eps = @($healthObj.results) }
  elseif ($healthObj.endpoints) { $eps = @($healthObj.endpoints) }
  foreach ($e in $eps) {
    $group = ''
    if ($e.PSObject.Properties.Name -contains 'name') {
      if (('' + $e.name) -like 'agent_*') { $group = 'agent' }
      if (('' + $e.name) -like 'phone_*') { $group = 'phone' }
    }
    $okFlag = $false
    if ($e.PSObject.Properties.Name -contains 'ok') { $okFlag = [bool]$e.ok }
    if ($group -eq 'agent') { $agentTotal += 1; if ($okFlag) { $agentOk += 1 } }
    if ($group -eq 'phone') { $phoneTotal += 1; if ($okFlag) { $phoneOk += 1 } }
  }
  Write-Host ("AGENT OK: {0}/{1}" -f $agentOk, $agentTotal)
  Write-Host ("PHONE OK: {0}/{1}" -f $phoneOk, $phoneTotal)
  Print-Endpoints -Obj $healthObj
}

# -----------------------------------------------------------------------------
# 6) Footer
# -----------------------------------------------------------------------------
$status = "OK"
if (-not $up) { $status = "FAIL agent_not_responding" }
if ($healthErr) { $status = "WARN health_unavailable" }

Write-Host "PACK: [NOT CREATED]"
Write-Host ("STATUS: {0}" -f $status)
Write-Host "python ./tools/show_next_step.py"
