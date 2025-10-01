<# 
PA-361/PA-370 Bootstrap (UI auto-mount + watchdog non-blocking)
#>
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Ensure-Dir([string]$p){ if (-not (Test-Path $p)) { New-Item -ItemType Directory -Force -Path $p | Out-Null } }

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

# 2) Update config\processes.json (server cmd -> bootstrap)
$cfgPath = Join-Path $RepoRoot 'config\processes.json'
$cfg = $null
if (Test-Path $cfgPath) {
  try { $cfg = Get-Content $cfgPath -Raw | ConvertFrom-Json -ErrorAction Stop } catch { $cfg = $null }
}
if ($null -eq $cfg) {
  $cfg = @{ processes = @{} }
}
if ($null -eq $cfg.processes) {
  $cfg.processes = @{}
}

# server process
$server = $cfg.processes.server
if ($null -eq $server) {
  $server = @{ name = "server"; cmd = @("python","-u","-m","server.bootstrap_mounts") }
} else {
  $server.name = "server"
  $server.cmd  = @("python","-u","-m","server.bootstrap_mounts")
}
$cfg.processes.server = $server

# tunnel process (preserve if present; otherwise add a sensible default)
if ($null -eq $cfg.processes.tunnel) {
  $cfExe = "C:\Program Files\Cloudflare\cloudflared\cloudflared.exe"
  $cfg.processes.tunnel = @{
    name = "tunnel";
    depends_on = @("server");
    cmd  = @($cfExe,"tunnel","--no-autoupdate","--url","http://127.0.0.1:8776");
    logs = @{ stdout = "tmp\logs\cloudflared.out.log"; stderr = "tmp\logs\cloudflared.err.log" };
    health = @{ log_regex = "https?://\S*trycloudflare\.com"; publish = @{ file = "reports\ops\tunnel_url.txt" } };
    restart = @{ policy = "on-failure" };
  }
}

# write config
($cfg | ConvertTo-Json -Depth 8) | Set-Content -Encoding UTF8 $cfgPath

# 3) Ensure tunnel URL monitor injected into tools\ps1\run_watchdog.ps1
$runWd = Join-Path $RepoRoot 'tools\ps1\run_watchdog.ps1'
if (Test-Path $runWd) {
  $marker = 'TUNNEL URL MONITOR (PA-361)'
  $txt = Get-Content $runWd -Raw
  if ($txt -notmatch [regex]::Escape($marker)) {
    $mon = @'
# --- TUNNEL URL MONITOR (PA-361) ---
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
# --- /TUNNEL URL MONITOR ---
'@
    Add-Content -Path $runWd -Value "`r`n$mon`r`n"
    Write-Host "[MONITOR] Injected tunnel URL monitor"
  } else {
    Write-Host "[MONITOR] Monitor already present"
  }
} else {
  Write-Warning "Missing tools\ps1\run_watchdog.ps1; tunnel monitor not injected."
}

# 4) Commit
try { git add -A; git commit -m "PA-361/370: bootstrap mounts + config; non-blocking smoke" | Out-Null } catch {}

# 5) Restart watchdog
try { pwsh -NoProfile -ExecutionPolicy Bypass -File (Join-Path $RepoRoot 'tools\ps1\stop_watchdog.ps1') } catch {}
pwsh -NoProfile -ExecutionPolicy Bypass -File (Join-Path $RepoRoot 'tools\ps1\run_watchdog.ps1')

# 6) Non-blocking smoke (best-effort; short timeouts)
Ensure-Dir "tmp\logs"
$smokeLog = "tmp\logs\pack_smoke.txt"
$u = "http://127.0.0.1:8776"
$result = @{}
try {
  $h = Invoke-WebRequest "$u/healthz" -TimeoutSec 2 -UseBasicParsing
  $result.healthz = $h.StatusCode
} catch { $result.healthz = "fail: $($_.Exception.Message)" }
try {
  $a = Invoke-WebRequest "$u/api/watchdog" -TimeoutSec 2 -UseBasicParsing
  $result.api_watchdog = $a.StatusCode
} catch { $result.api_watchdog = "fail: $($_.Exception.Message)" }
try {
  $m = Invoke-WebRequest "$u/__debug" -TimeoutSec 2 -UseBasicParsing
  $result.debug = $m.StatusCode
} catch { $result.debug = "fail: $($_.Exception.Message)" }

($result | ConvertTo-Json -Depth 5) | Set-Content -Encoding UTF8 $smokeLog
Write-Host "==== BOOTSTRAP APPLIED ===="
Write-Host "Smoke written to $smokeLog"
