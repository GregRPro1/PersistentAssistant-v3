Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$pidFile = "tmp\pid\watchdog.pid"
if (-not (Test-Path $pidFile)) { Write-Host "No PID file ($pidFile). Nothing to stop."; exit 0 }
$wdPid = 0
try { $wdPid = [int](Get-Content $pidFile -Raw) } catch {}
$proc = $null
if ($wdPid -gt 0) { $proc = Get-Process -Id $wdPid -ErrorAction SilentlyContinue }

if ($proc) {
  try { $proc.CloseMainWindow() | Out-Null } catch {}
  Start-Sleep -Milliseconds 500
  try { $proc.Kill() } catch {}
  Write-Host "Stopped watchdog (PID $wdPid)"
} else {
  Write-Host "No running process found for PID $wdPid"
}
Remove-Item $pidFile -ErrorAction SilentlyContinue
