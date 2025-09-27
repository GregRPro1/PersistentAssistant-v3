$ErrorActionPreference='Stop'
# Manual one-shot poll; respects config/email_watch.yaml.
$root = $env:PA_REPO_ROOT
if (-not $root) { $root = 'C:\_Repos\PersistentAssistant' }
if (-not (Test-Path $root)) { Write-Error "Repo root not found at $root"; exit 2 }
Set-Location $root

$py = Join-Path $root '.venv\Scripts\python.exe'
if (-not (Test-Path $py)) { $py = 'python' }

& $py 'tools\py\email_watcher.py'
exit $LASTEXITCODE
