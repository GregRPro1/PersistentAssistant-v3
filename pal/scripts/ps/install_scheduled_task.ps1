param([string]$ConfigPath = ".\pal\config\pal_watchdog.json")
$script = Join-Path $PSScriptRoot "..\..\core\health\watchdog.ps1"; $script = (Resolve-Path $script).Path
$action = New-ScheduledTaskAction -Execute "pwsh.exe" -Argument "-NoProfile -WindowStyle Hidden -File `"$script`" -ConfigPath `"$ConfigPath`""
$trigger = New-ScheduledTaskTrigger -AtLogOn
Register-ScheduledTask -TaskName "PAL-Watchdog" -Action $action -Trigger $trigger -Description "Start PAL watchdog at logon" -RunLevel Highest -Force
Write-Host "Scheduled task 'PAL-Watchdog' installed."
