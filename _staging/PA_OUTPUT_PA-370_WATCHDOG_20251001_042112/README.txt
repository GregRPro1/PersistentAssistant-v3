PA-370 Watchdog Pack (20251001_042112)

Includes:
- watchdog/pa_watchdog.py (supervisor)
- config/processes.json (server + tunnel)
- tools/ps1/run_watchdog.ps1, tools/ps1/stop_watchdog.ps1

Use:
  pwsh tools\ps1\run_watchdog.ps1
  # status written to reports\ops\watchdog_status.json

Next:
- I'll ship a small UI pack to add a status card on /app that reads this JSON.
