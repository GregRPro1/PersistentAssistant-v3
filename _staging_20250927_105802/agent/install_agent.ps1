
param([string]$RepoRoot="C:\_Repos\PersistentAssistant",[string]$TaskName="PA_InboxAgent")
$ErrorActionPreference='Stop'
$watch = Join-Path $RepoRoot "agent\agent_watch.ps1"
if(-not (Test-Path $watch)){ throw "Missing agent\agent_watch.ps1" }
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$watch`""
$trigger = New-ScheduledTaskTrigger -AtLogOn
try { Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue } catch {}
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Description "PA Folder Watcher" | Out-Null
Start-ScheduledTask -TaskName $TaskName
Write-Host "Folder watcher installed & started."
