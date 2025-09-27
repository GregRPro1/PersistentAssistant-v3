param([switch]$ProcessLocal)
$ErrorActionPreference='Stop'
# Wrapper sets working dir, picks venv python if present, runs watcher.
$root = $env:PA_REPO_ROOT
if (-not $root) { $root = 'C:\_Repos\PersistentAssistant' }
if (-not (Test-Path $root)) { Write-Error "Repo root not found at $root"; exit 2 }
Set-Location $root

$py = Join-Path $root '.venv\Scripts\python.exe'
if (-not (Test-Path $py)) { $py = 'python' }

$env:PYTHONUNBUFFERED='1'
$env:PA_REPO_ROOT=$root

# Ensure logs dir exists
$log = Join-Path $root 'reports\ops\email_watch.run.log'
New-Item -ItemType Directory -Force -Path (Split-Path $log -Parent) | Out-Null
Add-Content -Path $log -Value ("{0} starting watcher (ProcessLocal={1})" -f (Get-Date -Format s), $ProcessLocal)

$args = @('tools\py\email_watcher.py')
if ($ProcessLocal) { $args += '--process-local' }

& $py @args
$ec = $LASTEXITCODE
Add-Content -Path $log -Value ("{0} exit={1}" -f (Get-Date -Format s), $ec)
exit $ec
