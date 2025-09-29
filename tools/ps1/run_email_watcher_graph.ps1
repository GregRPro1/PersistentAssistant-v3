param([switch]$DeviceLogin)
$ErrorActionPreference='Stop'
$root = $env:PA_REPO_ROOT; if (-not $root) { $root = 'C:\_Repos\PersistentAssistant' }
if (-not (Test-Path $root)) { Write-Error "Repo root not found at $root"; exit 2 }
Set-Location $root
pwsh -File 'tools\ps1\install_deps.ps1' | Write-Host
$py = Join-Path $root '.venv\Scripts\python.exe'; if (-not (Test-Path $py)) { $py = 'python' }
$env:PYTHONUNBUFFERED='1'; $env:PA_REPO_ROOT=$root
$log = Join-Path $root 'reports\ops\email_watch_graph.run.log'
New-Item -ItemType Directory -Force -Path (Split-Path $log -Parent) | Out-Null
Add-Content -Path $log -Value ("{0} starting graph watcher (DeviceLogin={1})" -f (Get-Date -Format s), $DeviceLogin)
$args = @('tools\py\email_watcher_graph.py'); if ($DeviceLogin) { $args += '--device-login' }
& $py @args
$ec = $LASTEXITCODE
Add-Content -Path $log -Value ("{0} exit={1}" -f (Get-Date -Format s), $ec)
exit $ec
