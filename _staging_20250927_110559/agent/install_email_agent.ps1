
param([string]$RepoRoot="C:\_Repos\PersistentAssistant",[string]$TaskName="PA_EmailPoller",[int]$EveryMinutes=1)
$ErrorActionPreference='Stop'
$runner = Join-Path $RepoRoot "agent\run_email_poll.ps1"
$config = Join-Path $RepoRoot "agent\email_config.yaml"
if(-not (Test-Path $runner) -or -not (Test-Path $config)){ throw "Missing email poller files" }
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes $EveryMinutes) -RepetitionDuration ([TimeSpan]::MaxValue)
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$runner`""
try { Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue } catch {}
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Description "PA Email Poller ($EveryMinutes min)" | Out-Null
Start-ScheduledTask -TaskName $TaskName
Write-Host "Email poller installed & started."
