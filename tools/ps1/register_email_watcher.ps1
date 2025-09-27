$ErrorActionPreference='Stop'
$taskName = 'PA_EmailWatcher'
$cmd = 'python tools\\py\\email_watcher.py'
schtasks /Create /SC MINUTE /MO 5 /TN $taskName /TR $cmd /RL HIGHEST /F
Write-Host "Scheduled task '$taskName' created to run every 5 minutes."
