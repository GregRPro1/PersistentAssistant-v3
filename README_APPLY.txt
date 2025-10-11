# PAL — Demo Fix & Force Ops

This pack includes:
- Updated **watchdog.ps1** (again, with robust LAN-IP) — writes phone.lan + phone.url.
- Resilient **pal_demo_verify.ps1** — prints Phone URL even if ops_status.json has no 'phone' yet by computing LAN host:port from config.

## Apply
pwsh .\scripts\apply_pack.ps1 -ZipPath "$env:USERPROFILE\Downloads\PAL_Demo_Fix_and_Force_Ops.zip"

## Run
pwsh .\pal\core\health\watchdog.ps1
pwsh .\pal\scripts\ps\pal_demo_verify.ps1 -TaskId PAL-DEMO
