$ErrorActionPreference="SilentlyContinue"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$repo = Resolve-Path (Join-Path $here "..")
Set-Location $repo
Start-Process -WindowStyle Hidden -FilePath (Get-Command powershell).Source -ArgumentList @("-NoLogo","-NoProfile","-ExecutionPolicy","Bypass","-File","tools\approvals_watchdog.ps1","-Port","8781","-Every","5","-MaxRestarts","3") | Out-Null
