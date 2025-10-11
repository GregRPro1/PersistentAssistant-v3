# PAL — Watchdog Fix + Demo Smoke

This patch:
- Replaces **pal/core/health/watchdog.ps1** with a robust LAN-IP detector and ensures it writes:
  ```json
  "phone": { "lan": "http://<lan-ip>:<port>", "url": "http://<lan-ip>:<port>" or tunnel }
  ```
- Adds **pal/scripts/ps/pal_demo_verify.ps1** to create a demo smoke PASS and print the **Phone URL**.

## Apply
```powershell
cd C:\_Repos\PersistentAssistant
pwsh .\scripts\apply_pack.ps1 -ZipPath "$env:USERPROFILE\Downloads\PAL_Watchdog_Fix_and_Demo_Smoke.zip"
```

## Run
```powershell
# Start watchdog (it will populate reports\ops\ops_status.json)
pwsh .\pal\core\health\watchdog.ps1

# In another terminal, emit demo smoke and show the Phone URL
pwsh .\pal\scripts\ps\pal_demo_verify.ps1 -TaskId PAL-DEMO
```
You should see: `Phone URL: http://192.168.x.x:8787` (or your tunnel URL), and the tracker will refresh showing **Phone** instead of N/A.
