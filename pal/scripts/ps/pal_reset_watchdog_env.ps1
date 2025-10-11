# Stop tracker, web, cloudflared; clear bad tunnel; restart watchdog and nudge tracker
Set-StrictMode -Version Latest
$ErrorActionPreference = "Continue"

function Kill-ByNameLike([string]$pattern){
  $procs = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match $pattern }
  foreach ($p in $procs) { try { Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue } catch {} }
}

Write-Host "Stopping tracker/web/cloudflared ..."
Kill-ByNameLike "pal[\\/]ui[\\/]desktop[\\/]pal_tracker\.py"
Kill-ByNameLike "current[\\/]server\.py"
Kill-ByNameLike "cloudflared"

Write-Host "Clearing bad tunnel and forcing ops snapshot ..."
pwsh .\pal\scripts\ps\clear_bad_tunnel.ps1 | Out-Host
pwsh .\pal\scripts\ps\pal_force_ops_snapshot.ps1 | Out-Host

Write-Host "Starting watchdog (in this console) ..."
Write-Host "Tip: run in another window if you want to keep this one free."
pwsh .\pal\core\health\watchdog.ps1
