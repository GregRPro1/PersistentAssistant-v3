param(
  [switch]$Repair,         # stop+start watchdog
  [switch]$FixFirewall,    # try to open port 8776 (needs admin)
  [switch]$RestartTunnel,  # ask watchdog to restart tunnel
  [switch]$Watch,          # loop every N seconds
  [int]$IntervalSeconds = 8
)

$ErrorActionPreference='SilentlyContinue'
function Write-Light([string]$label, [bool]$ok, [string]$detail=""){
  $e = if($ok){"🟢"}else{"🔴"}; if($detail){ Write-Host "$e $label — $detail" } else { Write-Host "$e $label" }
}
function Try-Get($url,$timeout=5){
  try{ (Invoke-WebRequest -UseBasicParsing -TimeoutSec $timeout -Uri $url).StatusCode }catch{ $_.Exception.Message }
}
function Is-Listening($port){
  try{ [bool](Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue) }catch{ $false }
}
function Stop-8776(){
  Get-NetTCPConnection -LocalPort 8776 -State Listen -ErrorAction SilentlyContinue |
    ForEach-Object { try{ Stop-Process -Id $_.OwningProcess -Force }catch{} }
}
function Restart-Watchdog(){
  try{ pwsh tools\ps1\stop_watchdog.ps1 | Out-Null }catch{}
  Start-Sleep -Milliseconds 400
  try{ pwsh tools\ps1\run_watchdog.ps1 | Out-Null }catch{}
}
function Open-Firewall8776(){
  try{ pwsh tools\ps1\open_firewall_port.ps1 -Port 8776 -Name "PA 8776" -Force | Out-Null; return $true }catch{ return $false }
}
function Resolve-Modules(){
  $py = ".\.venv\Scripts\python.exe"
  if(!(Test-Path $py)){ return @("🔴 venv python missing at $py") }
  New-Item -ItemType Directory -Force tmp | Out-Null
  $tmpPy = "tmp\resolve_modules.py"
  @"
import importlib
mods = ["pa_lan","server.pa_lan","server.watchdog_api","server.watchdog_ui","server.bootstrap_mounts"]
for m in mods:
    try:
        mod = importlib.import_module(m)
        p = getattr(mod, "__file__", "built-in") or "built-in"
        print(f"{m} => {p}")
    except Exception as e:
        print(f"{m} => (err: {e})")
"@ | Set-Content -LiteralPath $tmpPy -Encoding UTF8
  & $py $tmpPy
}
function Latest-ServerLogPath(){
  $err="tmp\logs\server.err.log"; $out="tmp\logs\server.out.log"
  $et=(Test-Path $err)?(Get-Item $err).LastWriteTime:(Get-Date 0)
  $ot=(Test-Path $out)?(Get-Item $out).LastWriteTime:(Get-Date 0)
  if($ot -gt $et){ return $out } else { return $err }
}
function Probe($base){
  $o = [ordered]@{}
  $o.base = $base
  $o.port_listen = Is-Listening 8776
  # healthz
  $o.health_code = Try-Get "$base/healthz" 3
  $o.health_ok = ($o.health_code -is [int] -and $o.health_code -eq 200)

  # routes
  $dbg = $null
  try{ $dbg = (Invoke-WebRequest "$base/__debug" -UseBasicParsing -TimeoutSec 4).Content }catch{}
  $o.debug_ok = [bool]$dbg
  $o.routes = if($dbg){ ($dbg -split "`r?`n") |?{$_ -match '^\s*/'} } else { @() }

  # API/UI (single + double)
  $o.api      = Try-Get "$base/api/watchdog" 5
  $o.api2x    = Try-Get "$base/api/api/watchdog" 5
  $o.ui       = Try-Get "$base/app/watchdog" 5
  $o.ui2x     = Try-Get "$base/app/app/watchdog" 5

  # tunnel url from file/logs (best-effort)
  $urls = @()
  if(Test-Path 'reports\ops\tunnel_url.txt'){
    $urls += ((Get-Content 'reports\ops\tunnel_url.txt' -TotalCount 1) -split '\s+')
  }
  foreach($p in @('tmp\logs\cloudflared.err.log','tmp\logs\cloudflared.out.log')){
    if(Test-Path $p){
      $m = Select-String -Path $p -Pattern 'https?://\S*trycloudflare\.com' -AllMatches
      if($m){ $urls += ($m.Matches | % Value) }
    }
  }
  $urls = $urls |?{$_} | Select-Object -Unique
  $o.tunnel_url = if($urls){ $urls[-1] } else { $null }
  $o.tunnel_health = if($o.tunnel_url){ Try-Get "$($o.tunnel_url)/healthz" 6 } else { $null }
  return $o
}
function Print-Lights($o){
  Write-Host ""
  Write-Light "Port 8776 listening" $o.port_listen
  Write-Light "Healthz 200" $o.health_ok
  $apiOK = ($o.api -is [int] -and $o.api -eq 200)
  $api2  = ($o.api2x -is [int] -and $o.api2x -eq 200)
  $uiOK  = ($o.ui  -is [int] -and $o.ui  -eq 200)
  $ui2   = ($o.ui2x -is [int] -and $o.ui2x -eq 200)
  Write-Light "API /api/watchdog" $apiOK ("$($o.api)")
  Write-Light "UI  /app/watchdog" $uiOK ("$($o.ui)")
  Write-Light "No double API (/api/api/watchdog)" (-not $api2) ("present=$api2")
  Write-Light "No double UI  (/app/app/watchdog)" (-not $ui2)  ("present=$ui2")
  Write-Light "Tunnel URL present" ([bool]$o.tunnel_url) ($o.tunnel_url ?? "")
  $extOK = ($o.tunnel_health -is [int] -and $o.tunnel_health -eq 200)
  Write-Light "External /healthz via tunnel" $extOK ("$($o.tunnel_health)")
  Write-Host ""
}
function One-Cycle($doRepair,$doFixFw,$doRestartTunnel){
  # Optional repairs first
  if($doFixFw){
    $fw = Open-Firewall8776
    Write-Host (($fw)? "🟢 Firewall rule ensured for 8776" : "🔴 Firewall rule attempt failed (need admin?).")
  }
  if($doRepair){
    Write-Host "… restarting watchdog/server"
    Stop-8776
    Restart-Watchdog
  }
  # Resolve active modules (tell us what is truly loaded)
  Write-Host "`n== Active Python modules =="
  Resolve-Modules | Write-Host

  # Wait for healthz
  $base = "http://127.0.0.1:8776"
  $deadline=(Get-Date).AddSeconds(18); $ok=$false
  while((Get-Date) -lt $deadline -and -not $ok){
    Start-Sleep -Milliseconds 600
    try{ $ok = ((Invoke-WebRequest "$base/healthz" -UseBasicParsing -TimeoutSec 2).StatusCode -eq 200) }catch{}
  }
  if($ok){ Write-Host "🟢 /healthz: 200" } else { Write-Host "🔴 /healthz: DOWN" }

  $o = Probe $base
  Print-Lights $o

  # Suggest next
  if(-not $o.health_ok){
    Write-Host "Next: Tail newest server log:"
    $p = Latest-ServerLogPath
    Write-Host "  Get-Content $p -Tail 120"
  } elseif(($o.api2x -is [int] -and $o.api2x -eq 200) -or ($o.ui2x -is [int] -and $o.ui2x -eq 200)){
    Write-Host "❌ Double-prefix detected. Run:"
    Write-Host "  pwsh tools\ps1\fix_double_routes.ps1"
    Write-Host "Then re-run:"
    Write-Host "  pwsh tools\ps1\pa_doctor.ps1 -Repair"
  } elseif($doRestartTunnel){
    try{
      Invoke-WebRequest -Method POST -UseBasicParsing -TimeoutSec 8 -Uri "$base/api/api/watchdog/tunnel/restart" | Out-Null
      Start-Sleep 2
      $o2 = Probe $base
      Write-Host "`nAfter tunnel restart:"
      Print-Lights $o2
    }catch{
      Write-Host "Tunnel restart call failed: $($_.Exception.Message)"
    }
  }
}

if($Watch){
  Write-Host "Watching… Ctrl+C to stop."
  while($true){ One-Cycle $Repair $FixFirewall $RestartTunnel; Start-Sleep -Seconds $IntervalSeconds }
}else{
  One-Cycle $Repair $FixFirewall $RestartTunnel
}
