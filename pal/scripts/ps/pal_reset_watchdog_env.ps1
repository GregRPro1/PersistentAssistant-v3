Set-StrictMode -Version Latest
$ErrorActionPreference = "Continue"
function Kill-ByPattern([string]$pat){ $procs = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match $pat }; foreach ($p in $procs) { try { Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue } catch {} } }
Write-Host "Stopping tracker/web/cloudflared ..."
Kill-ByPattern "pal[\/]ui[\/]desktop[\/]pal_tracker\.py"
Kill-ByPattern "current[\/]server\.py"
Kill-ByPattern "cloudflared"
Write-Host "Clearing bad tunnel and forcing ops snapshot ..."
pwsh .\pal\scripts\ps\clear_bad_tunnel.ps1 | Out-Host
pwsh .\pal\scripts\ps\pal_force_ops_snapshot.ps1 | Out-Host
Write-Host "Starting watchdog (in this console) ..."
pwsh .\pal\core\health\watchdog.ps1