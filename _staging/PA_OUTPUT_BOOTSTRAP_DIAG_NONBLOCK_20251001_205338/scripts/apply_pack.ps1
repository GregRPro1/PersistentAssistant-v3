<# 
PA Bootstrap + Diagnostics (non-blocking)
#>
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Ensure-Dir([string]$p){ if (-not (Test-Path $p)) { New-Item -ItemType Directory -Force -Path $p | Out-Null } }
function Tail([string]$p, [int]$n = 120){
  if (Test-Path $p) { try { return (Get-Content -Path $p -Tail $n -ErrorAction Stop) -join "`r`n" } catch { return "err: $($_.Exception.Message)" } }
  else { return "(missing)" }
}

$RepoRoot = Get-Location
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Payload  = Join-Path $ScriptDir '..\payload'

Write-Host "apply_pack: repo root = $RepoRoot"
if (-not (Test-Path $Payload)) { throw "Payload folder not found: $Payload" }

# 1) Copy payload files into repo
$files = Get-ChildItem -Recurse -File $Payload
foreach ($f in $files) {
  $rel = $f.FullName.Substring($Payload.Length).TrimStart('\','/')
  $dest = Join-Path $RepoRoot $rel
  $destDir = Split-Path $dest -Parent
  Ensure-Dir $destDir
  Copy-Item -Force -Path $f.FullName -Destination $dest
}

# 2) Update config\processes.json robustly
$cfgPath = Join-Path $RepoRoot 'config\processes.json'
$cfg = $null
if (Test-Path $cfgPath) {
  try { $cfg = ConvertFrom-Json -AsHashtable -InputObject (Get-Content $cfgPath -Raw) } catch { $cfg = @{} }
} else { $cfg = @{} }
if (-not $cfg.ContainsKey('processes') -or ($cfg.processes -isnot [hashtable])) { $cfg['processes'] = @{} }

# prefer venv python if present
$venvPy = Join-Path $RepoRoot '.venv\Scripts\python.exe'
$pyExe  = (Test-Path $venvPy) ? $venvPy : 'python'

$cfg['processes']['server'] = @{
  name = 'server'
  cmd  = @($pyExe,'-u','-m','server.bootstrap_mounts')
}

if (-not $cfg['processes'].ContainsKey('tunnel')) {
  $cfExe = 'C:\Program Files\Cloudflare\cloudflared\cloudflared.exe'
  $cfg['processes']['tunnel'] = @{
    name = 'tunnel'
    depends_on = @('server')
    cmd  = @($cfExe,'tunnel','--no-autoupdate','--url','http://127.0.0.1:8776')
    logs = @{ stdout = 'tmp\logs\cloudflared.out.log'; stderr = 'tmp\logs\cloudflared.err.log' }
    health = @{ log_regex = 'https?://\S*trycloudflare\.com'; publish = @{ file = 'reports\ops\tunnel_url.txt' } }
    restart = @{ policy = 'on-failure' }
  }
}

Ensure-Dir (Split-Path $cfgPath -Parent)
($cfg | ConvertTo-Json -Depth 12) | Set-Content -Encoding UTF8 $cfgPath
Write-Host "[CFG] processes.json updated"

# 3) Ensure tunnel URL monitor block in run_watchdog.ps1
$runWd = Join-Path $RepoRoot 'tools\ps1\run_watchdog.ps1'
if (-not (Test-Path $runWd)) { throw "Missing $runWd" }
$marker = 'TUNNEL URL MONITOR (PA-NONBLOCK)'
$present = Select-String -Path $runWd -SimpleMatch -Pattern $marker -Quiet
if (-not $present) {
  $mon = @'
# --- TUNNEL URL MONITOR (PA-NONBLOCK) ---
try {
  function Ensure-Dir([string]$p){ if (-not (Test-Path $p)) { New-Item -ItemType Directory -Force -Path $p | Out-Null } }
  $logDir = "tmp\logs"
  $outL = Join-Path $logDir "cloudflared.out.log"
  $errL = Join-Path $logDir "cloudflared.err.log"
  $pub  = "reports\ops\tunnel_url.txt"
  Ensure-Dir (Split-Path $pub -Parent)
  Start-Job -Name "pa_tunnel_monitor" -ScriptBlock {
    param($outL,$errL,$pub)
    $pattern = 'https?://\S*trycloudflare\.com'
    $wrote = $false
    while(-not $wrote){
      $hits = @()
      foreach($p in @($outL,$errL)){
        if (Test-Path $p) {
          $m = Select-String -Path $p -Pattern $pattern -AllMatches -ErrorAction SilentlyContinue
          if ($m) { $hits += ($m.Matches | ForEach-Object { $_.Value }) }
        }
      }
      if ($hits.Count -gt 0) {
        $first = [string]($hits | Select-Object -First 1)
        Set-Content -Encoding UTF8 -Path $pub -Value $first
        $wrote = $true
      } else {
        Start-Sleep -Milliseconds 700
      }
    }
  } -ArgumentList $outL,$errL,$pub | Out-Null
} catch {}
# --- /TUNNEL URL MONITOR (PA-NONBLOCK) ---
'@
  Add-Content -Path $runWd -Value "`r`n$mon`r`n"
  Write-Host "[MON] injected tunnel monitor"
} else {
  Write-Host "[MON] tunnel monitor already present"
}

# 4) Commit (no push)
try { git add -A; git commit -m "PA: non-blocking bootstrap + diag + tunnel monitor" | Out-Null } catch {}

# 5) Restart watchdog
try { pwsh -NoProfile -ExecutionPolicy Bypass -File (Join-Path $RepoRoot 'tools\ps1\stop_watchdog.ps1') | Out-Null } catch {}
pwsh -NoProfile -ExecutionPolicy Bypass -File (Join-Path $RepoRoot 'tools\ps1\run_watchdog.ps1') | Out-Null
Start-Sleep 3

# 6) Diagnostics: endpoints, mounts, logs, tunnel URL (non-fatal)
Ensure-Dir "tmp\logs"
$diag = [ordered]@{ when = (Get-Date).ToString("s"); repo = "$RepoRoot" }

function TryCall([string]$url){
  try {
    $r = Invoke-WebRequest $url -TimeoutSec 2 -UseBasicParsing
    return @{ code = $r.StatusCode; len = ($r.Content).Length; sample = ($r.Content.Substring(0, [Math]::Min(200, ($r.Content).Length))) }
  } catch {
    return @{ code = "fail"; error = $_.Exception.Message }
  }
}

$base = "http://127.0.0.1:8776"
$diag.endpoints = @{
  healthz = TryCall "$base/healthz"
  debug   = TryCall "$base/__debug"
  api_watchdog = TryCall "$base/api/watchdog"
}

# Mounts string (best effort from __debug sample)
$diag.mounts_hint = $diag.endpoints.debug.sample

# Logs tail
$diag.logs = @{
  watchdog_err   = Tail "tmp\logs\watchdog.err.log"
  watchdog_out   = Tail "tmp\logs\watchdog.out.log"
  server_err     = Tail "tmp\logs\server.err.log"
  server_out     = Tail "tmp\logs\server.out.log"
  cloudflared_err= Tail "tmp\logs\cloudflared.err.log"
  cloudflared_out= Tail "tmp\logs\cloudflared.out.log"
}

# Tunnel URL
$tunnelFile = "reports\ops\tunnel_url.txt"
if (Test-Path $tunnelFile) {
  $raw = (Get-Content $tunnelFile -TotalCount 1)
  $first = ($raw -split '\s+')[0]
  if ($first) { Set-Content -Encoding UTF8 $tunnelFile -Value $first }
  $diag.tunnel_url = $first
  $diag.phone_url  = "$first/app/watchdog"
} else {
  $diag.tunnel_url = "(missing)"
}

# Python version
$pyV = "(unknown)"
try { $pyV = & $pyExe --version 2>&1 } catch {}
$diag.python = $pyV

# Persist diag
$diagJson = ($diag | ConvertTo-Json -Depth 6)
$diagTxt  = $diagJson
Set-Content -Encoding UTF8 tmp\logs\pack_diag.json -Value $diagJson
Set-Content -Encoding UTF8 tmp\logs\pack_diag.txt  -Value $diagTxt

Write-Host "==== PACK APPLIED (non-blocking) ===="
if ($diag.phone_url) { Write-Host ("PHONE URL: {0}" -f $diag.phone_url) }
Write-Host "Diag: tmp\logs\pack_diag.txt"
