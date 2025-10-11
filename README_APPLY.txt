# PAL — Tunnel URL Validation Fix

**Problem**: `tunnel_url.txt` contained a stray "m", so the watchdog published `phone.url = "m"`.  
**Fix**: Validate the tunnel URL before using it; if invalid, prefer the LAN URL.

## Apply
```powershell
cd C:\_Repos\PersistentAssistant
pwsh .\scripts\apply_pack.ps1 -ZipPath "$env:USERPROFILE\Downloads\PAL_TunnelURL_Validation_Fix.zip"
```

## Use
### A) Clear the bad tunnel value now
```powershell
pwsh .\pal\scripts\ps\clear_bad_tunnel.ps1
type .\reports\ops\ops_status.json   # Phone.url should equal Phone.lan
```

### B) (Optional) Start a quick tunnel and write a proper URL
```powershell
pwsh .\pal\scripts\ps\run_quick_tunnel.ps1 -Port 8787
type .\reports\ops\tunnel_url.txt    # should be https://*.trycloudflare.com
```

### C) Watchdog will now:
- Only accept a tunnel URL if it’s a well-formed http(s) URL.
- Otherwise it leaves `tunnel.ok=false` and uses the LAN URL for `phone.url`.

This guarantees the tracker and WhatsApp share never see a single-letter "m" again.
