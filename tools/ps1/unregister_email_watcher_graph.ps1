$ErrorActionPreference='Stop'
$taskName = 'PA_GraphWatcher'
try { Unregister-ScheduledTask -TaskName $taskName -Confirm:$false | Out-Null; Write-Host "Scheduled task '$taskName' deleted." }
catch { Write-Error ("Unregister-ScheduledTask failed: " + $_.Exception.Message); exit 1 }
