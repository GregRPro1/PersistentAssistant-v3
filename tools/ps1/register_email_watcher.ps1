$ErrorActionPreference='Stop'
$taskName = 'PA_EmailWatcher'
$repo = $env:PA_REPO_ROOT
if (-not $repo) { $repo = 'C:\_Repos\PersistentAssistant' }
$cmd = "python `"$repo\tools\py\email_watcher.py`""
schtasks /Create /SC MINUTE /MO 1 /TN $taskName /TR $cmd /RL HIGHEST /F
Write-Host "Scheduled task '$taskName' created to run every 1 minute."
