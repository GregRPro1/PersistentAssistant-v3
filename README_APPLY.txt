# PAL Smoke Auto-Flip + Tracker Geometry Debounce

This pack:
- Auto-flips task status from smoke outputs (`reports/smoke/*.json`): **PASS → review**, **FAIL → blocked**.
- Background **smoke watcher** to handle non-blocking test runs.
- Tracker now **remembers window position/size** with a 2s debounce on move/resize (restores on restart).
- `run_smoke_all.ps1` updated to auto-flip when using `-Wait`.

## Apply
```powershell
cd C:\_Repos\PersistentAssistant
pwsh .\scripts\apply_pack.ps1 -ZipPath "$env:USERPROFILE\Downloads\PAL_Smoke_Autoflip_and_Tracker_Geometry_Debounce.zip"
# If your packer ignores payload/, expand manually and copy payload/* to repo root.
```

## Use
```powershell
# Run smokes non-blocking, then start watcher to auto-flip and refresh tracker:
pwsh .\pal\scripts\ps\run_smoke_all.ps1
Start-Job -ScriptBlock { pwsh .\pal\scripts\ps\smoke_watch.ps1 } | Out-Null

# Or run smokes and wait; statuses auto-flip at the end:
pwsh .\pal\scripts\ps\run_smoke_all.ps1 -Wait
```

## Optional: Integrate with watchdog
Add the following function to `pal\core\health\watchdog.ps1` and call it each loop:
(see `pal\core\health\watchdog.PATCH.txt` included in this pack). Then set in `pal\config\pal_watchdog.json`:
```json
"enable_smoke_watch": true
```

## Tracker geometry persistence
Move/resize the tracker; it writes `pal/config/pal_ui.json` after ~2s of inactivity and on close. On restart, it restores that geometry.

Generated: 2025-10-11
