$ErrorActionPreference='Stop'
function Test-Admin {
  $id=[Security.Principal.WindowsIdentity]::GetCurrent()
  $p = New-Object Security.Principal.WindowsPrincipal($id)
  return $p.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}
$taskName = 'PA_GraphWatcher'
$root = $env:PA_REPO_ROOT
if (-not $root) { $root = 'C:\_Repos\PersistentAssistant' }
if (-not (Test-Path $root)) { Write-Error "Repo root not found at $root"; exit 2 }
$wrapper = Join-Path $root 'tools\ps1\run_email_watcher_graph.ps1'
if (-not (Test-Path $wrapper)) { Write-Error "Wrapper not found at $wrapper"; exit 3 }
$pwsh = (Get-Command pwsh -ErrorAction SilentlyContinue)?.Source
if (-not $pwsh) { $pwsh = (Get-Command powershell -ErrorAction SilentlyContinue).Source }
if (-not $pwsh) { Write-Error "No PowerShell host found"; exit 4 }
$arg = "-WindowStyle Hidden -NoProfile -ExecutionPolicy Bypass -File `"$wrapper`""
$action = New-ScheduledTaskAction -Execute $pwsh -Argument $arg
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) `
    -RepetitionInterval (New-TimeSpan -Minutes 1) `
    -RepetitionDuration (New-TimeSpan -Days 3650)
$rl = 'Limited'; if (Test-Admin) { $rl = 'Highest' }
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -RunLevel $rl -Force | Out-Null
Write-Host "Scheduled task '$taskName' created (RunLevel=$rl)."
