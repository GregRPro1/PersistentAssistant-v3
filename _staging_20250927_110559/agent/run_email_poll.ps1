
param([string]$Config = ".\agent\email_config.yaml")
$ErrorActionPreference='SilentlyContinue'
function Resolve-Py { try { & python -V | Out-Null; "python" } catch { try { & py -3 -V | Out-Null; "py -3" } catch { $null } } }
$Py = Resolve-Py
if ($Py) { & $Py agent\email_poll.py -c $Config; exit $LASTEXITCODE } else { exit 10 }
