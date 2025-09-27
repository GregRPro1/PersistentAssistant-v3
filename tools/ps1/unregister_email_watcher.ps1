$ErrorActionPreference='Stop'
$taskName = 'PA_EmailWatcher'
schtasks /Delete /TN $taskName /F
Write-Host "Scheduled task '$taskName' deleted."
