$ErrorActionPreference='Stop'
$root = $env:PA_REPO_ROOT; if (-not $root) { $root = 'C:\_Repos\PersistentAssistant' }
if (-not (Test-Path $root)) { Write-Error "Repo root not found at $root"; exit 2 }
Set-Location $root
pwsh -File 'tools\ps1\install_deps.ps1' | Write-Host
$py = Join-Path $root '.venv\Scripts\python.exe'; if (-not (Test-Path $py)) { $py = 'python' }
& $py 'tools\py\email_watcher_graph.py'
exit $LASTEXITCODE
