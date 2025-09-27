$ErrorActionPreference='Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$script = Join-Path $root 'apply_inbox.ps1'
$taskName = 'PA_InboxApply'
schtasks /Create /SC MINUTE /MO 2 /TN $taskName /TR "pwsh -ExecutionPolicy Bypass -File `"$script`"" /RL HIGHEST /F
Write-Host "Scheduled task '$taskName' created to run every 2 minutes."
