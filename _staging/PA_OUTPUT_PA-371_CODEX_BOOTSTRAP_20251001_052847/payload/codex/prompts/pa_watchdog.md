# /pa_watchdog — Start/stop/status for the watchdog & tunnel

**Tasks you can run**:
- **Status**: `pwsh tools\ps1\codex\watchdog_status.ps1`
- **Restart server**: `pwsh tools\ps1\codex\watchdog_restart.ps1 -Name server`
- **Restart tunnel**: `pwsh tools\ps1\codex\watchdog_restart.ps1 -Name tunnel`
- **Start watchdog**: `pwsh tools\ps1\run_watchdog.ps1`
- **Stop watchdog**: `pwsh tools\ps1\stop_watchdog.ps1`
- **Get tunnel URL**: `pwsh tools\ps1\codex\tunnel_url.ps1`

**If a process is degraded/failed**:
- Tail logs with `Invoke-RestMethod http://127.0.0.1:8776/api/watchdog/logs/<name>` or open `/app/watchdog`.
- Suggest concrete code fixes and apply them, then restart that process.
