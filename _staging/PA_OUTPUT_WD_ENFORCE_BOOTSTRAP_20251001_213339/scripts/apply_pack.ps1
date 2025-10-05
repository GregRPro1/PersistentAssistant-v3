<# 
PA WD Enforce Bootstrap (non-blocking)
#>
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Ensure-Dir([string]$p){ if (-not (Test-Path $p)) { New-Item -ItemType Directory -Force -Path $p | Out-Null } }
function Tail([string]$p, [int]$n = 120){
  if (Test-Path $p) { try { return (Get-Content -Path $p -Tail $n -ErrorAction Stop) -join "`r`n" } catch { return "err: $($_.Exception.Message)" } }
  else { return "(missing)" }
}
function PidsOnPort([int]$port){
  $pids = @()
  try {
    $conns = Get-NetTCPConnection -LocalPort $port -ErrorAction Stop | Where-Object { $_.State -eq 'Listen' }
    $pids = $conns.OwningProcess | Sort-Object -Unique
  } catch {
    $lines = netstat -ano | Select-String (":$port\s") -ErrorAction SilentlyContinue
    foreach($l in $lines){
      $t = ($l.ToString() -split '\s+') | Where-Object { $_ -ne '' }
      if ($t.Length -ge 5) {
        $pid = $t[-1]
        if ($pid -match '^\d+$') { $pids += [int]$pid }
      }
    }
    $pids = $pids | Sort-Object -Unique
  }
  return ,$pids
}
function KillPid([int]$pid){
  try {
    $p = Get-Process -Id $pid -ErrorAction Stop
    $name = $p.ProcessName
    try { $p.CloseMainWindow() | Out-Null } catch {}
    Start-Sleep -Milliseconds 250
    try { Stop-Process -Id $pid -Force -ErrorAction Stop } catch {}
    return @{ pid=$pid; name=$name; killed=$true }
  } catch {
    return @{ pid=$pid; name=""; killed=$false; err=$_.Exception.Message }
  }
}

$RepoRoot = Get-Location
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Payload  = Join-Path $ScriptDir '..\payload'

Write-Host "apply_pack: repo root = $RepoRoot"
if (-not (Test-Path $Payload)) { throw "Payload folder not found: $Payload" }

$files = Get-ChildItem -Recurse -File $Payload
foreach ($f in $files) {
  $rel = $f.FullName.Substring($Payload.Length).TrimStart('\','/')
  $dest = Join-Path $RepoRoot $rel
  $destDir = Split-Path $dest -Parent
  Ensure-Dir $destDir
  Copy-Item -Force -Path $f.FullName -Destination $dest
}

$cfgPath = Join-Path $RepoRoot 'config\processes.json'
$cfg = $null
if (Test-Path $cfgPath) {
  try { $cfg = ConvertFrom-Json -AsHashtable -InputObject (Get-Content $cfgPath -Raw) } catch { $cfg = @{} }
} else { $cfg = @{} }
if (-not $cfg.ContainsKey('processes') -or ($cfg.processes -isnot [hashtable])) { $cfg['processes'] = @{} }

$venvPy = Join-Path $RepoRoot '.venv\Scripts\python.exe'
$pyExe  = (Test-Path $venvPy) ? $venvPy : 'python'
$cfg['processes']['server'] = @{ name='server'; cmd=@($pyExe,'-u','-m','server.bootstrap_mounts') }

Ensure-Dir (Split-Path $cfgPath -Parent)
($cfg | ConvertTo-Json -Depth 12) | Set-Content -Encoding UTF8 $cfgPath

$diag = [ordered]@{ when = (Get-Date).ToString("s"); pre = @{}; post = @{} }
$diag.pre.pids_8776 = PidsOnPort 8776

try { pwsh -NoProfile -ExecutionPolicy Bypass -File (Join-Path $RepoRoot 'tools\ps1\stop_watchdog.ps1') | Out-Null } catch {}

Get-Process cloudflared -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue

$left = PidsOnPort 8776
$killed = @()
foreach($pid in $left){ $killed += (KillPid $pid) }
$diag.pre.kill_attempts = $killed

Start-Sleep 600

pwsh -NoProfile -ExecutionPolicy Bypass -File (Join-Path $RepoRoot 'tools\ps1\run_watchdog.ps1') | Out-Null

$base = "http://127.0.0.1:8776"
$diag.post.pids_8776 = @()
for($i=0;$i -lt 8;$i++){
  Start-Sleep 1
  $diag.post.pids_8776 = PidsOnPort 8776
  try { $r = Invoke-WebRequest "$base/__wd_diag" -TimeoutSec 1 -UseBasicParsing; $diag.wd_diag = @{ code=$r.StatusCode; body=$r.Content }; break } catch {}
}

function TryCall([string]$url){
  try { $r = Invoke-WebRequest $url -TimeoutSec 2 -UseBasicParsing; return @{ code=$r.StatusCode; sample=$r.Content.Substring(0,[Math]::Min(240, $r.Content.Length)) } }
  catch { return @{ code="fail"; err=$_.Exception.Message } }
}
$diag.endpoints = @{
  healthz = TryCall "$base/healthz"
  debug   = TryCall "$base/__debug"
  api_watchdog = TryCall "$base/api/watchdog"
  ui_watchdog  = TryCall "$base/app/watchdog"
}

Ensure-Dir "tmp\logs"
$diag.logs = @{
  bootstrap_mounts = Tail "tmp\logs\bootstrap_mounts.log"
  watchdog_err     = Tail "tmp\logs\watchdog.err.log"
  watchdog_out     = Tail "tmp\logs\watchdog.out.log"
  server_err       = Tail "tmp\logs\server.err.log"
  server_out       = Tail "tmp\logs\server.out.log"
  cloudflared_err  = Tail "tmp\logs\cloudflared.err.log"
  cloudflared_out  = Tail "tmp\logs\cloudflared.out.log"
}
$tfile = "reports\ops\tunnel_url.txt"
if (Test-Path $tfile) {
  $raw = Get-Content $tfile -TotalCount 1
  $first = ($raw -split '\s+')[0]
  if ($first) { Set-Content -Encoding UTF8 $tfile -Value $first }
  $diag.tunnel_url = $first
  $diag.phone_url  = "$first/app/watchdog"
}

Ensure-Dir "tmp\logs"
($diag | ConvertTo-Json -Depth 8) | Set-Content -Encoding UTF8 "tmp\logs\pack_diag_enforce.json"
Set-Content -Encoding UTF8 "tmp\logs\pack_diag_enforce.txt" -Value (Get-Content "tmp\logs\pack_diag_enforce.json" -Raw)

Write-Host "==== ENFORCE BOOTSTRAP PACK APPLIED ===="
if ($diag.phone_url) { Write-Host ("PHONE URL: {0}" -f $diag.phone_url) }
Write-Host "Diag: tmp\logs\pack_diag_enforce.txt"
