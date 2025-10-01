<# 
PA-361 UI Mount + Tunnel URL monitor — apply
- Uses current working directory as repo root (not the script folder)
- Appends auto-mount block to pa_lan.py (root or server/)
- Ensures run_watchdog.ps1 launches a background job that publishes the first trycloudflare URL to reports\ops\tunnel_url.txt
#>
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Ensure-Dir([string]$p){ if (-not (Test-Path $p)) { New-Item -ItemType Directory -Force -Path $p | Out-Null } }

$RepoRoot = Get-Location
Push-Location $RepoRoot
Write-Host "apply_pack: repo root = $RepoRoot"

# 1) Auto-mount block
$autoMount = @'
# --- AUTO-MOUNT watchdog (PA-361) ---
try:
    from server.watchdog_api import bp as _wd_api
    app.register_blueprint(_wd_api)
except Exception as _e:
    pass
try:
    from server.watchdog_ui import bp as _wd_ui
    app.register_blueprint(_wd_ui)
except Exception as _e:
    pass
# --- /AUTO-MOUNT ---
'@

$lanCandidates = @(
  (Join-Path $RepoRoot 'pa_lan.py'),
  (Join-Path $RepoRoot 'server\pa_lan.py')
) | Where-Object { Test-Path $_ }

if ($lanCandidates.Count -eq 0) {
  Write-Warning "pa_lan.py not found in repo root or server/. Skipping blueprint auto-mount."
} else {
  foreach($lan in $lanCandidates){
    $txt = Get-Content $lan -Raw
    if ($txt -notmatch 'AUTO-MOUNT watchdog') {
      Add-Content -Path $lan -Value "`r`n$autoMount`r`n"
      Write-Host "[MOUNT] Added auto-mount to $lan"
    } else {
      Write-Host "[MOUNT] Already present in $lan"
    }
  }
}

# 2) Tunnel URL monitor job injection (idempotent)
$runWd = Join-Path $RepoRoot 'tools\ps1\run_watchdog.ps1'
if (Test-Path $runWd) {
  $injectMarker = '# --- TUNNEL URL MONITOR (PA-361) ---'
  $runTxt = Get-Content $runWd -Raw
  if ($runTxt -notmatch [regex]::Escape($injectMarker)) {
    $monitor = @'
# --- TUNNEL URL MONITOR (PA-361) ---
try {
  $logDir = "tmp\logs"
  $outL = Join-Path $logDir "cloudflared.out.log"
  $errL = Join-Path $logDir "cloudflared.err.log"
  $pub  = "reports\ops\tunnel_url.txt"
  Ensure-Dir (Split-Path $pub -Parent)
  Start-Job -Name "pa_tunnel_monitor" -ScriptBlock {
    param($outL,$errL,$pub)
    $pattern = 'https?://\S*trycloudflare\.com'
    $written = $false
    while(-not $written){
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
        $written = $true
      } else {
        Start-Sleep -Milliseconds 700
      }
    }
  } -ArgumentList $outL,$errL,$pub | Out-Null
} catch {}
# --- /TUNNEL URL MONITOR ---
'@
    Add-Content -Path $runWd -Value "`r`n$monitor`r`n"
    Write-Host "[MONITOR] Injected tunnel URL monitor into tools\ps1\run_watchdog.ps1"
  } else {
    Write-Host "[MONITOR] Already present in run_watchdog.ps1"
  }
} else {
  Write-Warning "tools\ps1\run_watchdog.ps1 not found; cannot inject monitor."
}

# Commit (no push)
try { git add -A; git commit -m "PA-361: auto-mount watchdog UI/API; add tunnel URL monitor" | Out-Null } catch {}

Write-Host "==== UI MOUNT + TUNNEL MONITOR APPLIED ===="
Write-Host "Restart watchdog to take effect: pwsh tools\ps1\stop_watchdog.ps1 ; pwsh tools\ps1\run_watchdog.ps1"
