$ErrorActionPreference='Stop'
$root = $env:PA_REPO_ROOT
if (-not $root) { $root = (Get-Item $PSScriptRoot).Parent.Parent.FullName }
if (-not (Test-Path (Join-Path $root '.git'))) { $root = 'C:\_Repos\PersistentAssistant' }
$cli = Join-Path $root 'tools\py\smoke_summary_cli.py'
if (-not (Test-Path $cli)) { Write-Host "smoke_summary_cli.py is missing at $cli"; exit 2 }
try { & python -V | Out-Null; $py='python' } catch { try { & py -3 -V | Out-Null; $py='py -3' } catch { $py=$null } }
if (-not $py) { Write-Error 'Python 3 not found on PATH'; exit 1 }
& $py $cli --out-html (Join-Path $root 'reports\smoke\index.html') | Write-Host
$index = Join-Path $root 'reports\smoke\index.html'
if (Test-Path $index) { Start-Process $index } else { Write-Host "No smoke html at $index" }
