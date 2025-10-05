<# 
PA WD Enforce Bootstrap (MAXDIAG, non-blocking)
- Copies payload/*
- Forces server runner -> python -u -m server.bootstrap_mounts
- Stops watchdog; clears port 8776 listeners (no $PID collisions)
- Restarts watchdog, probes routes, persists diagnostics ALWAYS
- Does NOT modify pytest.ini; does NOT prompt
#>
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Ensure-Dir([string]$p){ if (-not (Test-Path $p)) { New-Item -ItemType Directory -Force -Path $p | Out-Null } }
function Tail([string]$p, [int]$n = 160){
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
        $p = $t[-1]
        if ($p -match '^\d+$') { $pids += [int]$p }
      }
    }
    $pids = $pids | Sort-Object -Unique
  }
  return ,$pids
}
function KillProcId([int]$procId){
  try {
    $p = Get-Process -Id $procId -ErrorAction Stop
    $name = $p.ProcessName
    try { $p.CloseMainWindow() | Out-Null } catch {}
    Start-Sleep -Milliseconds 250
    try { Stop-Process -Id $procId -Force -ErrorAction Stop } catch {}
    return @{ pid=$procId; name=$name; killed=$true }
  } catch {
    return @{ pid=$procId; name=""; killed=$false; err=$_.Exception.Message }
  }
}
function TryCall([string]$url,[int]$timeout=2){
  try { $r = Invoke-WebRequest $url -TimeoutSec $timeout -UseBasicParsing; 
        return @{ code=$r.StatusCode; len=$r.Content.Length; sample=$r.Content.Substring(0,[Math]::Min(240, $r.Content.Length)) } }
  catch { return @{ code="fail"; err=$_.Exception.Message } }
}
function Find-Python([string]$repo){
  $candidates = @(
    (Join-Path $repo '.venv\Scripts\python.exe'),
    "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe",
    "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
    "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe",
    "$env:ProgramFiles\Python313\python.exe",
    "$env:ProgramFiles\Python312\python.exe",
    "$env:ProgramFiles\Python311\python.exe"
  ) | Where-Object { $_ -and (Test-Path $_) }
  if ($candidates.Count -gt 0) { return $candidates[0] }
  $py = Get-Command python -ErrorAction SilentlyContinue
  if ($py) { return $py.Source }
  $py = Get-Command py -ErrorAction SilentlyContinue
  if ($py) { return $py.Source }
  return "python"
}

$RepoRoot = Get-Location
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Payload  = Join-Path $ScriptDir '..\payload'

Ensure-Dir "tmp\logs"
$diagPath = "tmp\logs\pack_diag_enforce.txt"
$diagJson = "tmp\logs\pack_diag_enforce.json"
$diag = [ordered]@{ when = (Get-Date).ToString("s"); steps=@(); results=@{} }
function Save-Diag(){ ($diag | ConvertTo-Json -Depth 8) | Set-Content -Encoding UTF8 $diagJson; Set-Content -Encoding UTF8 $diagPath -Value (Get-Content $diagJson -Raw) }

try {
  $diag.steps += "copy_payload"
  if (-not (Test-Path $Payload)) { throw "Payload folder not found: $Payload" }
  $files = Get-ChildItem -Recurse -File $Payload
  foreach ($f in $files) {
    $rel = $f.FullName.Substring($Payload.Length).TrimStart('\','/')
    $dest = Join-Path $RepoRoot $rel
    $destDir = Split-Path $dest -Parent
    Ensure-Dir $destDir
    # Don't overwrite user's watchdog modules; only deploy fallbacks
    if ($rel -ieq 'server\watchdog_api.py' -or $rel -ieq 'server\watchdog_ui.py') {
      if (-not (Test-Path $dest)) { Copy-Item -Force -Path $f.FullName -Destination $dest }
    } else {
      Copy-Item -Force -Path $f.FullName -Destination $dest
    }
  }

  $diag.steps += "python_detect"
  $pyExe = Find-Python $RepoRoot
  $diag.results.python = @{ exe=$pyExe; version=(try { & $pyExe -V 2>&1 } catch { "(unknown)" }) }

  $diag.steps += "update_processes_json"
  $cfgPath = Join-Path $RepoRoot 'config\processes.json'
  $cfg = $null
  if (Test-Path $cfgPath) {
    try { $cfg = ConvertFrom-Json -AsHashtable -InputObject (Get-Content $cfgPath -Raw) } catch { $cfg = @{} }
  } else { $cfg = @{} }
  if (-not $cfg.ContainsKey('processes') -or ($cfg.processes -isnot [hashtable])) { $cfg['processes'] = @{} }
  $cfg['processes']['server'] = @{ name='server'; cmd=@($pyExe,'-u','-m','server.bootstrap_mounts') }
  Ensure-Dir (Split-Path $cfgPath -Parent)
  ($cfg | ConvertTo-Json -Depth 12) | Set-Content -Encoding UTF8 $cfgPath
  $diag.results.processes_json = Get-Content $cfgPath -Raw

  $diag.steps += "stop_watchdog_and_clear_port"
  try { pwsh -NoProfile -ExecutionPolicy Bypass -File (Join-Path $RepoRoot 'tools\ps1\stop_watchdog.ps1') | Out-Null } catch {}
  Get-Process cloudflared -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
  $pre = PidsOnPort 8776
  $diag.results.pre_pids_8776 = $pre
  $killRes = @()
  foreach($procId in $pre){ $killRes += (KillProcId $procId) }
  $diag.results.kill_attempts = $killRes
  Start-Sleep 1000

  $diag.steps += "start_watchdog"
  $runWd = Join-Path $RepoRoot 'tools\ps1\run_watchdog.ps1'
  if (Test-Path $runWd) {
    pwsh -NoProfile -ExecutionPolicy Bypass -File $runWd | Out-Null
    $diag.results.start_mode = "watchdog_script"
  } else {
    # Fallback: start server directly (no tunnel) - best effort
    Start-Process -FilePath $pyExe -ArgumentList @('-u','-m','server.bootstrap_mounts') -WindowStyle Hidden
    $diag.results.start_mode = "direct_python_fallback"
  }

  $diag.steps += "probe_local_endpoints"
  $base = "http://127.0.0.1:8776"
  for($i=0;$i -lt 15;$i++){
    Start-Sleep 1
    $ping = TryCall "$base/healthz" 1
    if ($ping.code -ne "fail") { break }
  }
  $diag.results.endpoints = @{
    healthz = TryCall "$base/healthz"
    debug   = TryCall "$base/__debug"
    runner  = TryCall "$base/__runner"
    wd_diag = TryCall "$base/__wd_diag"
    api_watchdog = TryCall "$base/api/watchdog"
    ui_watchdog  = TryCall "$base/app/watchdog"
  }

  $diag.steps += "collect_logs"
  $diag.results.logs = @{
    bootstrap_mounts = Tail "tmp\logs\bootstrap_mounts.log"
    watchdog_err     = Tail "tmp\logs\watchdog.err.log"
    watchdog_out     = Tail "tmp\logs\watchdog.out.log"
    server_err       = Tail "tmp\logs\server.err.log"
    server_out       = Tail "tmp\logs\server.out.log"
    cloudflared_err  = Tail "tmp\logs\cloudflared.err.log"
    cloudflared_out  = Tail "tmp\logs\cloudflared.out.log"
  }

  $diag.steps += "phone_url"
  $tfile = "reports\ops\tunnel_url.txt"
  if (Test-Path $tfile) {
    $raw = Get-Content $tfile -TotalCount 1
    $first = ($raw -split '\s+')[0]
    if ($first) { Set-Content -Encoding UTF8 $tfile -Value $first }
    $diag.results.tunnel_url = $first
    $diag.results.phone_url  = "$first/app/watchdog"
    $diag.results.phone_probe = TryCall $diag.results.phone_url 3
  } else {
    # Best-effort extraction from logs
    $pattern = 'https?://\S*trycloudflare\.com'
    $hits = @()
    foreach($p in @('tmp\logs\cloudflared.out.log','tmp\logs\cloudflared.err.log')){
      if (Test-Path $p) {
        $m = Select-String -Path $p -Pattern $pattern -AllMatches -ErrorAction SilentlyContinue
        if ($m) { $hits += ($m.Matches | ForEach-Object { $_.Value }) }
      }
    }
    if ($hits.Count -gt 0) {
      $first = [string]($hits | Select-Object -First 1)
      Ensure-Dir (Split-Path $tfile -Parent)
      Set-Content -Encoding UTF8 -Path $tfile -Value $first
      $diag.results.tunnel_url = $first
      $diag.results.phone_url  = "$first/app/watchdog"
      $diag.results.phone_probe = TryCall $diag.results.phone_url 3
    }
  }

} catch {
  $diag.results.error = $_.Exception.Message
} finally {
  Save-Diag
  Write-Host "==== ENFORCE BOOTSTRAP PACK (MAXDIAG) APPLIED ===="
  Write-Host "Diag: $diagPath"
  if ($diag.results.phone_url) { Write-Host ("PHONE URL: {0}" -f $diag.results.phone_url) }
}
