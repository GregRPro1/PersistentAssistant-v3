$ErrorActionPreference='Stop'
# Robust scheduler: uses wrapper PS1, handles non-admin by falling back to LIMITED, checks errors.

function Test-Admin {
  $id=[Security.Principal.WindowsIdentity]::GetCurrent()
  $p = New-Object Security.Principal.WindowsPrincipal($id)
  return $p.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

$taskName = 'PA_EmailWatcher'
$root = $env:PA_REPO_ROOT
if (-not $root) { $root = 'C:\_Repos\PersistentAssistant' }
$wrapper = Join-Path $root 'tools\ps1\run_email_watcher.ps1'
if (-not (Test-Path $wrapper)) { Write-Error "Wrapper not found at $wrapper"; exit 2 }

# Prefer pwsh, fallback to powershell.exe
$ps = (Get-Command pwsh -ErrorAction SilentlyContinue).Path
if (-not $ps) { $ps = (Get-Command powershell -ErrorAction SilentlyContinue).Path }
if (-not $ps) { Write-Error "No PowerShell host found"; exit 3 }

$rl = 'HIGHEST'
if (-not (Test-Admin)) { $rl = 'LIMITED' }

# Build command line. We quote wrapper and pass no args (default IMAP mode from config).
$TR = "$ps -NoProfile -ExecutionPolicy Bypass -File `"$wrapper`""

# Create/replace task
$cmd = @('schtasks','/Create','/SC','MINUTE','/MO','1','/TN',$taskName,'/TR',$TR,'/RL',$rl,'/F')
$proc = Start-Process -FilePath $cmd[0] -ArgumentList $cmd[1..($cmd.Length-1)] -NoNewWindow -PassThru -Wait
if ($proc.ExitCode -ne 0) {
  Write-Error "schtasks failed with exit code $($proc.ExitCode). Try running as Administrator or use Task Scheduler UI."
  exit $proc.ExitCode
}
Write-Host "Scheduled task '$taskName' created to run every 1 minute (RunLevel=$rl)."
