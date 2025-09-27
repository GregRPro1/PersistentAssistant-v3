$ErrorActionPreference='Stop'
$root = $env:PA_REPO_ROOT
if (-not $root) { $root = (Get-Item $PSScriptRoot).Parent.Parent.FullName }
if (-not (Test-Path (Join-Path $root '.git'))) { $root = 'C:\_Repos\PersistentAssistant' }
try { & python -V | Out-Null; $py='python' } catch { try { & py -3 -V | Out-Null; $py='py -3' } catch { $py=$null } }
if (-not $py) { Write-Error 'Python 3 not found on PATH'; exit 1 }
& $py (Join-Path $root 'tools\py\devstep_catalog.py')
$index = Join-Path $root 'reports\dev\index.html'
if (Test-Path $index) { Start-Process $index } else { Write-Host "No dev catalog at $index" }
