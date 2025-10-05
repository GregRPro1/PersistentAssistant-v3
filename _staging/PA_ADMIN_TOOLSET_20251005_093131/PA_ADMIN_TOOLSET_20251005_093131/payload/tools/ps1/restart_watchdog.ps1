
pwsh tools\ps1\stop_watchdog.ps1 | Out-Null
Start-Sleep -Milliseconds 700
pwsh tools\ps1\run_watchdog.ps1  | Out-Null
Write-Host "Watchdog restarted."
