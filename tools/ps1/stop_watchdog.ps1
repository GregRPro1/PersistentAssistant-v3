Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$pidFile = "tmp\pid\watchdog.pid"
if (-not (Test-Path $pidFile)) { Write-Host "No PID file ($pidFile). Nothing to stop."; exit 0 }
$pid = Get-Content $pidFile
$proc = Get-Process -Id ([int]$pid) -ErrorAction SilentlyContinue
if ($proc) {
  try { $proc.CloseMainWindow() | Out-Null } catch {}
  Start-Sleep -Seconds 1
  try { $proc.Kill() } catch {}
  Write-Host "Stopped watchdog (PID $pid)"
} else {
  Write-Host "No running process found for PID $pid"
}
Remove-Item $pidFile -ErrorAction SilentlyContinue
