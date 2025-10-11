# PAL — Watchdog Restart + Geometry + Phone URL fixes

This patch delivers:
- **watchdog.ps1**: robust tracker restart (`Stop-Tracker` kills python processes whose command line includes `pal/ui/desktop/pal_tracker.py`). Handles both `{"command":"restart","target":"tracker"}` and `{"command":"restart_tracker"}`.
- **pal_force_ops_snapshot.ps1**: fixed PowerShell hashtable (no inline `if`), writes `phone.lan/url` immediately.
- **pal_tracker.py**: persists window geometry (saved every 5s and on close; restored on startup). Status bar computes Phone URL fallback if watchdog hasn't written it yet.

## Apply
cd C:\_Repos\PersistentAssistant
pwsh .\scripts\apply_pack.ps1 -ZipPath "$env:USERPROFILE\Downloads\PAL_Watchdog_Restart_Geometry_Fixes.zip"

## Verify
# 1) Force ops snapshot so Phone shows up immediately
pwsh .\pal\scripts\ps\pal_force_ops_snapshot.ps1
type .\reports\ops\ops_status.json

# 2) Restart via watchdog request (now guaranteed to kill old tracker and relaunch)
'{"command":"restart","target":"tracker"}' | Set-Content .\pal\control\requests\restart_tracker.json -Encoding UTF8

# 3) Drag tracker window somewhere, close, re-open — it should restore position/size.
