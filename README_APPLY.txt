# PAL P1 Non-Blocking Parallel

This pack sets up **phase-level** helpers so you can flip every task in a phase to `in_progress`, generate smoke stubs for them, and run the smokes **in parallel** (non-blocking or with `-Wait`).

### Apply
```powershell
cd C:\_Repos\PersistentAssistant
pwsh .\scripts\apply_pack.ps1 -ZipPath "$env:USERPROFILE\Downloads\PAL_P1_NonBlocking_Parallel.zip"
```

### Colors (tracker)
- **Green** = `done`
- **Amber + bold** = `in_progress`
- **Blue/Cyan** = `review` (this is what you saw after PASS)
- **Red** = `blocked`

### Run for P1
```powershell
# 1) Mark all P1 tasks in progress (turns amber + bold) and refresh tracker
pwsh .\pal\scripts\ps\pal_set_phase_inprogress.ps1 -Phase P1

# 2) Generate missing smoke test stubs for phase P1
pwsh .\pal\scripts\ps\gen_smoke_for_phase.ps1 -Phase P1

# 3) Fire smokes in parallel (non-blocking)
pwsh .\pal\scripts\ps\run_smoke_phase.ps1 -Phase P1

# (optional) Block and auto-flip to review/blocked at the end
pwsh .\pal\scripts\ps\run_smoke_phase.ps1 -Phase P1 -Wait
```

The existing smoke watcher from the previous pack will auto-flip statuses when new results appear and restart the tracker to reflect changes.
