# PAL Tracker Approve-in-UI + Start P2

**Colors:** grey=todo, amber(in‑progress)=in_progress, blue=review (smoke PASS), red=blocked (smoke FAIL), green=done.

This pack:
- Adds **Approve → Done** and quick status buttons inside the tracker (right pane).
- Shows **Last smoke: PASS/FAIL @ timestamp** per selected task.
- Shows **Watcher: ON/OFF** in the status bar (heartbeat file).
- Refreshes smoke watcher script to write the heartbeat.

## Apply
```powershell
cd C:\_Repos\PersistentAssistant
pwsh .\scripts\apply_pack.ps1 -ZipPath "$env:USERPROFILE\Downloads\PAL_Tracker_Approve_UI_and_P2_Start.zip"
```

## Start P2 quickly (non-blocking)
```powershell
pwsh .\pal\scripts\ps\pal_set_phase_inprogress.ps1 -Phase P2
pwsh .\pal\scripts\ps\gen_smoke_for_phase.ps1 -Phase P2
pwsh .\pal\scripts\ps\run_smoke_phase.ps1 -Phase P2
# optional: ensure watcher running
Start-Job -ScriptBlock { pwsh .\pal\scripts\ps\smoke_watch.ps1 } | Out-Null
```
