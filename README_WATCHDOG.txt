
WATCHDOG USAGE
==============
Apply:
  pwsh .\apply_packs_only.ps1 -ZipPath "$env:USERPROFILE\Downloads\PAL20251012A_watchdog.zip"

Config:
  Edit .\watchdog\watchdog.yaml
  - Set TunnelName in the cloudflared command, or remove cloudflared entry until login is complete.
  - Adjust ports/commands as needed.

One-off actions:
  # Kill ports used by services (frees 8787 etc.)
  pwsh -File .\scripts\watchdog\watchdog.ps1 -Action killports

  # Start all services (pal-dev-server, cloudflared)
  pwsh -File .\scripts\watchdog\watchdog.ps1 -Action start

  # Stop all services
  pwsh -File .\scripts\watchdog\watchdog.ps1 -Action stop

  # Restart all services cleanly
  pwsh -File .\scripts\watchdog\watchdog.ps1 -Action restart

  # Status (health + ports)
  pwsh -File .\scripts\watchdog\watchdog.ps1 -Action status

Continuous supervise (single instance):
  pwsh -File .\scripts\watchdog\watchdog.ps1 -Action run

Logs: .\logs\watchdog\watchdog_YYYYMMDD.log
