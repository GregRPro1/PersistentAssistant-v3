$ErrorActionPreference='Stop'
try { & python -V | Out-Null; $py='python' } catch { try { & py -3 -V | Out-Null; $py='py -3' } catch { $py=$null } }
if (-not $py) { Write-Error 'Python 3 not found on PATH'; exit 1 }
& $py (Join-Path $PSScriptRoot '..\tools\py\smoke_summary_cli.py')
