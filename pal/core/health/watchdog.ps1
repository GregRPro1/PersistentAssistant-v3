param(
  [string]$ConfigPath = ".\pal\config\pal_watchdog.json",
  [int]$IntervalSec = 5
)
Set-StrictMode -Version Latest
$ErrorActionPreference = "Continue"

function NowIso { (Get-Date).ToString("s") }
function Ensure-Dir([string]$p){ if (-not (Test-Path $p)) { New-Item -ItemType Directory -Force -Path $p | Out-Null } }

function Tcp-Check([string]$Host, [int]$Port, [int]$TimeoutMs=1500) {
  try { $c = New-Object System.Net.Sockets.TcpClient
    $iar = $c.BeginConnect($Host, $Port, $null, $null)
    if (-not $iar.AsyncWaitHandle.WaitOne($TimeoutMs)) { $c.Close(); return $false }
    $c.EndConnect($iar); $c.Close(); return $true
  } catch { return $false }
}

function Http-Check([string]$Url, [int]$TimeoutSec=3) {
  try { $req = [System.Net.WebRequest]::Create($Url)
    $req.Method = "GET"; $req.Timeout = $TimeoutSec*1000
    $resp = $req.GetResponse(); $resp.Close(); return $true
  } catch { return $false }
}

function Get-LanIp {
  try {
    $ip = (Get-NetIPAddress -AddressFamily IPv4 |
      Where-Object { $_.IPAddress -notmatch '^169\.' -and $_.IPAddress -notmatch '^127\.' -and
        ($_.IPAddress -match '^(10\.|192\.168\.|172\.(1[6-9]|2[0-9]|3[0-1])\.)') } |
      Select-Object -First 1 -ExpandProperty IPAddress)
    return $ip
  } catch { return $null }
}

function Write-OpsStatus([hashtable]$st){
  Ensure-Dir ".\reports\ops"
  ($st | ConvertTo-Json -Depth 6) | Set-Content ".\reports\ops\ops_status.json" -Encoding UTF8
}

function Read-Json([string]$p){ try { Get-Content $p -Raw -ErrorAction Stop | ConvertFrom-Json } catch { $null } }

function Is-GoodUrl([string]$u) {
  if (-not $u) { return $false }
  try {
    if ([Uri]::IsWellFormedUriString($u, [UriKind]::Absolute)) {
      $uri = [Uri]$u
      if ($uri.Scheme -in @("http","https")) { return $true }
    }
  } catch {}
  return $false
}

# Load config (tolerant defaults)
$cfg = Read-Json $ConfigPath
if (-not $cfg) {
  $cfg = @{
    web = @{ enabled=$true; host="127.0.0.1"; port=8787; health="http://127.0.0.1:8787/healthz"; run_script=".\\current\\run.ps1" }
    tracker = @{ enabled=$true; run_script="python .\\pal\\ui\\desktop\\pal_tracker.py" }
    smoke_watch = @{ enabled=$true; run_script="pwsh .\\pal\\scripts\\ps\\smoke_watch.ps1" }
    tunnel = @{ enabled=$false; url_file=".\\reports\\ops\\tunnel_url.txt" }
  }
}

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

function Stop-Tracker {
  try {
    if ($procs["tracker"]) { try { $procs["tracker"].Kill() } catch {} ; $procs["tracker"] = $null }
    $procsCim = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match "pal[\\/]ui[\\/]desktop[\\/]pal_tracker\.py" }
    foreach ($p in $procsCim) { try { Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue } catch {} }
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

  $tunnelUrl = ""
  if ($cfg.tunnel.enabled -and (Test-Path $cfg.tunnel.url_file)) {
    $raw = (Get-Content $cfg.tunnel.url_file -ErrorAction SilentlyContinue | Select-Object -First 1).Trim()
    if (Is-GoodUrl $raw) { $tunnelUrl = $raw }
  }

  $lanIp = Get-LanIp
  $phoneLan = if ($lanIp) { "http://$($lanIp):$($webPort)" } else { "" }
  $phoneUrl = if ($tunnelUrl) { $tunnelUrl } else { $phoneLan }

  $st = @{
    ts = NowIso
    web = @{ host=$webHost; port=$webPort; port_ok=$portOk; health_url=$health; health_ok=$healthOk }
    watcher = @{ on = $watchHb }
    tunnel = @{ url = $tunnelUrl; ok = (Is-GoodUrl $tunnelUrl) }
    phone = @{ lan = $phoneLan; url = $phoneUrl }
  }
  Write-OpsStatus $st
}

# main loop
Ensure-Dir ".\pal\control\requests"
Ensure-Dir ".\reports\ops"
while ($true) {
  try {
    Ensure-Running
    Snapshot

    $reqs = Get-ChildItem ".\pal\control\requests" -Filter *.json -File -ErrorAction SilentlyContinue
    foreach ($r in $reqs) {
      $obj = Read-Json $r.FullName
      if ($obj) {
        switch ($obj.command) {
          "restart" {
            if ($obj.target -eq "tracker") { Stop-Tracker }
            if ($obj.target -eq "web" -and $procs["web"]) { try { $procs["web"].Kill() } catch {} ; $procs["web"] = $null }
          }
          "restart_tracker" { Stop-Tracker }
          default { }
        }
      }
      Remove-Item $r.FullName -Force -ErrorAction SilentlyContinue
    }
  } catch {}
  Start-Sleep -Seconds $IntervalSec
}
