param(
  [string]$ConfigPath = ".\pal\config\pal_watchdog.json",
  [int]$IntervalSec = 5
)
Set-StrictMode -Version Latest
$ErrorActionPreference = "Continue"

function NowIso { (Get-Date).ToString("s") }

function Ensure-Dir([string]$p){ if (-not (Test-Path $p)) { New-Item -ItemType Directory -Force -Path $p | Out-Null } }

function Tcp-Check([string]$Host, [int]$Port, [int]$TimeoutMs=1500) {
  try {
    $c = New-Object System.Net.Sockets.TcpClient
    $iar = $c.BeginConnect($Host, $Port, $null, $null)
    if (-not $iar.AsyncWaitHandle.WaitOne($TimeoutMs)) { $c.Close(); return $false }
    $c.EndConnect($iar); $c.Close(); return $true
  } catch { return $false }
}

function Http-Check([string]$Url, [int]$TimeoutSec=3) {
  try {
    $wc = New-Object System.Net.WebClient
    $wc.Encoding = [System.Text.Encoding]::UTF8
    $wc.Headers.Add("User-Agent","PAL-Watchdog/1.0")
    $wc.BaseAddress = $Url
    $wc.CachePolicy = New-Object System.Net.Cache.RequestCachePolicy([System.Net.Cache.RequestCacheLevel]::NoCacheNoStore)
    $req = [System.Net.WebRequest]::Create($Url)
    $req.Method = "GET"; $req.Timeout = $TimeoutSec*1000
    $resp = $req.GetResponse(); $resp.Close(); return $true
  } catch { return $false }
}

function Write-OpsStatus([hashtable]$st){
  Ensure-Dir ".\reports\ops"
  ($st | ConvertTo-Json -Depth 6) | Set-Content ".\reports\ops\ops_status.json" -Encoding UTF8
}

function Read-Json([string]$p){ try { Get-Content $p -Raw -ErrorAction Stop | ConvertFrom-Json } catch { $null } }

# Load config (create default if missing)
if (-not (Test-Path $ConfigPath)) {
  $default = @{
    web = @{ enabled=$true; host="127.0.0.1"; port=8787; health="http://127.0.0.1:8787/healthz"; run_script=".\\current\\run.ps1" }
    tracker = @{ enabled=$true; run_script="python .\\pal\\ui\\desktop\\pal_tracker.py"; plan="pal\\plan\\pal_project_plan.yaml" }
    smoke_watch = @{ enabled=$true; run_script="pwsh .\\pal\\scripts\\ps\\smoke_watch.ps1" }
    tunnel = @{ enabled=$false; url_file=".\\reports\\ops\\tunnel_url.txt" }
  }
  Ensure-Dir (Split-Path $ConfigPath -Parent)
  ($default | ConvertTo-Json -Depth 6) | Set-Content $ConfigPath -Encoding UTF8
}

$cfg = Read-Json $ConfigPath
if (-not $cfg) { Write-Host "Invalid config: $ConfigPath"; exit 1 }

$procs = @{}

function Start-Cmd([string]$key, [string]$cmdline){
  if ($procs[$key]) { return }
  try {
    $si = New-Object System.Diagnostics.ProcessStartInfo
    $si.FileName = "pwsh"
    $si.Arguments = "-NoProfile -Command $cmdline"
    $si.UseShellExecute = $false
    $si.RedirectStandardOutput = $true
    $si.RedirectStandardError  = $true
    $p = New-Object System.Diagnostics.Process
    $p.StartInfo = $si
    $null = $p.Start()
    $procs[$key] = $p
  } catch {}
}

function Ensure-Running(){
  if ($cfg.web.enabled) { Start-Cmd "web" $cfg.web.run_script }
  if ($cfg.tracker.enabled) { Start-Cmd "tracker" $cfg.tracker.run_script }
  if ($cfg.smoke_watch.enabled) { Start-Cmd "smoke" $cfg.smoke_watch.run_script }
}

function Snapshot(){
  $webHost = $cfg.web.host; $webPort = [int]$cfg.web.port
  $health  = [string]$cfg.web.health
  $portOk  = Tcp-Check $webHost $webPort
  $healthOk= if ($health) { Http-Check $health 3 } else { $false }
  $watchHb = Test-Path ".\reports\smoke\_watcher_heartbeat.txt" -and ((Get-Date) - (Get-Item ".\reports\smoke\_watcher_heartbeat.txt").LastWriteTime).TotalSeconds -lt 20
  $tunnelUrl = ""; if ($cfg.tunnel.enabled -and (Test-Path $cfg.tunnel.url_file)) { $tunnelUrl = (Get-Content $cfg.tunnel.url_file -ErrorAction SilentlyContinue | Select-Object -First 1) }

  $st = @{
    ts = NowIso
    web = @{ host=$webHost; port=$webPort; port_ok=$portOk; health_url=$health; health_ok=$healthOk }
    watcher = @{ on = $watchHb }
    tunnel = @{ url = $tunnelUrl; ok = ($tunnelUrl -ne "") }
  }
  Write-OpsStatus $st
}

# main loop with request queue
Ensure-Dir ".\pal\control\requests"
Ensure-Dir ".\reports\ops"
while ($true) {
  try {
    Ensure-Running
    Snapshot

    # handle simple restart requests (files under pal/control/requests/*.json)
    $reqs = Get-ChildItem ".\pal\control\requests" -Filter *.json -File -ErrorAction SilentlyContinue
    foreach ($r in $reqs) {
      $obj = Read-Json $r.FullName
      if ($obj -and $obj.command -eq "restart") {
        if ($obj.target -eq "tracker" -and $procs["tracker"]) { try { $procs["tracker"].Kill() } catch {} ; $procs["tracker"] = $null }
        if ($obj.target -eq "web" -and $procs["web"]) { try { $procs["web"].Kill() } catch {} ; $procs["web"] = $null }
      }
      Remove-Item $r.FullName -Force -ErrorAction SilentlyContinue
    }
  } catch {}
  Start-Sleep -Seconds $IntervalSec
}
