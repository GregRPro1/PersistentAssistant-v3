# PAL Parallel Smoke 101..106

This pack adds **non-blocking, parallel smoke tests** for **PAL-101..PAL-106**, plus helpers to flip their status to `in_progress` and refresh the tracker.
It also tweaks the tracker so **in-progress items are bold** (and already amber).

## Apply
```powershell
cd C:\_Repos\PersistentAssistant
pwsh .\scripts\apply_pack.ps1 -ZipPath "$env:USERPROFILE\Downloads\PAL_Parallel_Smoke_101_106.zip"
# If your packer ignores payload/, expand manually and copy payload/* to repo root.
```

## Mark 101..106 in progress (turns tasks amber and bold in tracker)
```powershell
pwsh .\pal\scripts\ps\pal_set_inprogress_101_106.ps1
```

## Run smoke tests in parallel (non-blocking)
```powershell
# fire and forget (non-blocking)
pwsh .\pal\scripts\ps\run_smoke_all.ps1

# or wait for completion
pwsh .\pal\scripts\ps\run_smoke_all.ps1 -Wait
```

Results land in `reports/smoke/*.json` (one per task).

Generated: 2025-10-11
