param([string]$TaskName="PAL_Watchdog")
$repo = "C:\_Repos\PersistentAssistant"
$py = Join-Path $repo ".venv\Scripts\python.exe"
$script = Join-Path $repo "scripts\watchdog\watchdog_ui.py"
$action = New-ScheduledTaskAction -Execute $py -Argument $script -WorkingDirectory $repo
$trigger = New-ScheduledTaskTrigger -AtLogOn
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Description "Start PAL Watchdog UI at logon" -Force | Out-Null
Write-Host "Registered scheduled task '$TaskName' to start watchdog on logon."
