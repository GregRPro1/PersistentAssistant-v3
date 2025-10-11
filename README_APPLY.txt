# PAL — Full Tunnel/Phone Fix + Reset

This pack fixes the "m" tunnel bug permanently, gives you tools to clear bad values,
capture a valid trycloudflare URL, and **reset** the environment under the watchdog.

## Apply
pwsh .\scripts\apply_pack.ps1 -ZipPath "$env:USERPROFILE\Downloads\PAL_Full_Tunnel_Phone_Fix_and_Reset.zip"

## One-line reset (kills tracker/web/cloudflared, clears tunnel, restarts watchdog)
pwsh .\pal\scripts\ps\pal_reset_watchdog_env.ps1

## Quick tunnel (optional)
pwsh .\pal\scripts\ps\run_quick_tunnel.ps1 -Port 8787
type .\reports\ops\tunnel_url.txt

## Sanity
pwsh .\pal\scripts\ps\pal_print_phone.ps1
type .\reports\ops\ops_status.json
