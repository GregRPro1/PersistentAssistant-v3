# tools\ps1\stop_watchdog.ps1
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Continue'

$pidFile = "tmp\pid\watchdog.pid"
if (Test-Path $pidFile) {
  try {
    $pid = [int]((Get-Content $pidFile -Raw).Trim())
    $p = Get-Process -Id $pid -ErrorAction SilentlyContinue
    if ($p) {
      Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
      Write-Host "Stopped watchdog (PID $pid)"
    }
    else {
      Write-Host "No running process found for PID $pid"
    }
  }
  catch { Write-Host "No valid PID file"; }
  Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
}
else {
  Write-Host "No PID file ($pidFile). Nothing to stop."
}

# Kill helper jobs if present
foreach ($name in @("pa_watchdog_stdout", "pa_watchdog_stderr", "pa_tunnel_monitor", "pa_watchdog_heartbeat")) {
  $j = Get-Job -Name $name -ErrorAction SilentlyContinue
  if ($j) { Stop-Job $j -Force -ErrorAction SilentlyContinue; Remove-Job $j -Force -ErrorAction SilentlyContinue }
}
