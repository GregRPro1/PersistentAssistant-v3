Param([string]$TunnelName = "", [string]$TunnelUUID = "", [string]$LogFile = "C:\_Repos\PersistentAssistant\logs\cloudflared\foreground_run.log")
$ErrorActionPreference = "Stop"
$cf = Get-Command cloudflared -ErrorAction SilentlyContinue; if (-not $cf) { throw "cloudflared not in PATH" }
$runArgs = @("tunnel","--loglevel","debug","run")
if ($TunnelName) { $runArgs += $TunnelName } elseif ($TunnelUUID) { $runArgs += $TunnelUUID }
"Launching: cloudflared $($runArgs -join ' ')" | Tee-Object -FilePath $LogFile -Append
cloudflared @runArgs 2>&1 | Tee-Object -FilePath $LogFile -Append
