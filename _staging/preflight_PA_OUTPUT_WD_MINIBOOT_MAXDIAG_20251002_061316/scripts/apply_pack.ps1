
# ENFORCE BOOTSTRAP (MINIBOOT MAXDIAG) — no try/catch to avoid env parser issues
$ErrorActionPreference = 'Continue'

function Ensure-Dir([string]$p){ if (-not (Test-Path $p)) { New-Item -ItemType Directory -Force -Path $p | Out-Null } }
function Tail([string]$p, [int]$n = 160){
  if (Test-Path $p) { (Get-Content -Path $p -Tail $n -ErrorAction SilentlyContinue) -join "`r`n" } else { "(missing)" }
}
function PidsOnPort([int]$port){
  $pids = @()
  $conns = @()
  $hasNetTCP = Get-Command Get-NetTCPConnection -ErrorAction SilentlyContinue
  if ($hasNetTCP) {
    $conns = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue | Where-Object { $_.State -eq 'Listen' }
    if ($conns) { $pids += ($conns | Select-Object -ExpandProperty OwningProcess | Sort-Object -Unique) }
  }
  if (-not $pids -or $pids.Count -eq 0) {
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
  ,$pids
}
function TryCall2([string]$url, [int]$timeout=2){
  $r = Invoke-WebRequest $url -TimeoutSec $timeout -UseBasicParsing -ErrorAction SilentlyContinue
  if ($r) { @{ code=$r.StatusCode; len=($r.Content|Out-String).Length; sample=($r.Content|Out-String).Substring(0, [Math]::Min(240, ($r.Content|Out-String).Length)) } }
  else { @{ code="fail" } }
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
  "python"
}

$RepoRoot = Get-Location
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Payload  = Join-Path $ScriptDir '..\payload'

Ensure-Dir "tmp\logs"
$diagPath = "tmp\logs\pack_diag_enforce.txt"
$diagJson = "tmp\logs\pack_diag_enforce.json"
$diag = [ordered]@{ when = (Get-Date).ToString("s"); steps=@(); results=@{} }

# 1) Copy payload
$diag.steps += "copy_payload"
if (Test-Path $Payload) {
  $files = Get-ChildItem -Recurse -File $Payload
  foreach ($f in $files) {
    $rel = $f.FullName.Substring($Payload.Length).TrimStart('\','/')
    $dest = Join-Path $RepoRoot $rel
    Ensure-Dir (Split-Path $dest -Parent)
    Copy-Item -Force -Path $f.FullName -Destination $dest -ErrorAction SilentlyContinue
  }
} else {
  $diag.results.copy_error = "Payload missing: $Payload"
}

# 2) Python detect
$diag.steps += "python_detect"
$pyExe = Find-Python $RepoRoot
$pyVer = & $pyExe -V 2>&1
$diag.results.python = @{ exe=$pyExe; version=$pyVer }

# 3) Update processes.json to enforce bootstrap runner
$diag.steps += "update_processes_json"
$cfgPath = Join-Path $RepoRoot 'config\processes.json'
$serverCmd = @($pyExe,'-u','-m','server.bootstrap_mounts')
$cfg = @{}
if (Test-Path $cfgPath) {
  $raw = Get-Content $cfgPath -Raw -ErrorAction SilentlyContinue
  if ($raw) { $parsed = $null; $parsed = $raw | ConvertFrom-Json -AsHashtable -ErrorAction SilentlyContinue; if ($parsed) { $cfg = $parsed } }
}
if (-not $cfg.ContainsKey('processes')) { $cfg['processes'] = @{} }
$cfg['processes']['server'] = @{ name='server'; cmd=$serverCmd }
Ensure-Dir (Split-Path $cfgPath -Parent)
($cfg | ConvertTo-Json -Depth 12) | Set-Content -Encoding UTF8 $cfgPath
$diag.results.processes_json = Get-Content $cfgPath -Raw

# 4) Stop watchdog & clear port 8776
$diag.steps += "stop_watchdog_and_clear_port"
$stopScript = Join-Path $RepoRoot 'tools\ps1\stop_watchdog.ps1'
if (Test-Path $stopScript) { pwsh -NoProfile -ExecutionPolicy Bypass -File $stopScript | Out-Null }
Get-Process cloudflared -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
$pids = PidsOnPort 8776
$killed = @()
foreach($procId in $pids){
  $p = Get-Process -Id $procId -ErrorAction SilentlyContinue
  if ($p) {
    $p.CloseMainWindow() | Out-Null
    Start-Sleep -Milliseconds 200
    Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
    $killed += @{ pid=$procId; name=$p.ProcessName; killed=$true }
  } else {
    $killed += @{ pid=$procId; name=""; killed=$false }
  }
}
$diag.results.pre_pids_8776 = $pids
$diag.results.kill_attempts = $killed

# 5) Start watchdog or direct server
$diag.steps += "start_watchdog"
$runWd = Join-Path $RepoRoot 'tools\ps1\run_watchdog.ps1'
if (Test-Path $runWd) {
  pwsh -NoProfile -ExecutionPolicy Bypass -File $runWd | Out-Null
  $diag.results.start_mode = "watchdog_script"
} else {
  Start-Process -FilePath $pyExe -ArgumentList @('-u','-m','server.bootstrap_mounts') -WindowStyle Hidden
  $diag.results.start_mode = "direct_python_fallback"
}

# 6) Probe local endpoints (up to ~15s)
$diag.steps += "probe_local_endpoints"
$base = "http://127.0.0.1:8776"
$ok = $false
for($i=0;$i -lt 15;$i++){
  Start-Sleep 1
  $ping = TryCall2 "$base/healthz" 1
  if ($ping -and $ping.code -ne "fail") { $ok = $true; break }
}
$diag.results.endpoints = @{
  healthz = TryCall2 "$base/healthz"
  debug   = TryCall2 "$base/__debug"
  runner  = TryCall2 "$base/__runner"
  wd_diag = TryCall2 "$base/__wd_diag"
  api_watchdog = TryCall2 "$base/api/watchdog"
  ui_watchdog  = TryCall2 "$base/app/watchdog"
}

# 7) Collect logs
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

# 8) Phone URL normalization and probe
$diag.steps += "phone_url"
$tfile = "reports\ops\tunnel_url.txt"
$diag.results['tunnel_url'] = $null
$diag.results['phone_url'] = $null
if (Test-Path $tfile) {
  $raw = Get-Content $tfile -TotalCount 1 -ErrorAction SilentlyContinue
  if ($raw) {
    $first = ($raw -split '\s+')[0]
    if ($first) {
      Ensure-Dir (Split-Path $tfile -Parent)
      Set-Content -Encoding UTF8 -Path $tfile -Value $first
      $diag.results['tunnel_url'] = $first
      $diag.results['phone_url']  = "$first/app/watchdog"
      $diag.results['phone_probe'] = TryCall2 $diag.results['phone_url'] 3
    }
  }
}
if (-not $diag.results['phone_url']) {
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
    $diag.results['tunnel_url'] = $first
    $diag.results['phone_url']  = "$first/app/watchdog"
    $diag.results['phone_probe'] = TryCall2 $diag.results['phone_url'] 3
  }
}

# 9) Persist diagnostics (both JSON and text)
Ensure-Dir (Split-Path $diagPath -Parent)
($diag | ConvertTo-Json -Depth 10) | Set-Content -Encoding UTF8 $diagJson
Set-Content -Encoding UTF8 -Path $diagPath -Value (Get-Content $diagJson -Raw)

Write-Host "==== MINIBOOT MAXDIAG APPLIED ===="
Write-Host "Diag: $diagPath"
if ($diag.results.ContainsKey('phone_url') -and $diag.results['phone_url']) {
  Write-Host ("PHONE URL: {0}" -f $diag.results['phone_url'])
} else {
  Write-Host "PHONE URL: (not available yet)"
}
