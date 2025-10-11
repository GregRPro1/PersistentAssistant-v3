# PAL — Tracker Goalposts + Approve-in-UI + LLM Fix

This pack delivers:
- **Tracker UI**: gold **goalpost** banner (per phase), right-pane **Approve → Done** and quick status buttons, last-smoke info, watcher badge.
- **LLM adapter fix**: `doc_to_yaml.py` now imports adapters so **Registry.get('openai')** works.
- **Plan goalposts**: script to inject goalposts for M0..P3 and restart the tracker.

## Apply
```powershell
cd C:\_Repos\PersistentAssistant
pwsh .\scripts\apply_pack.ps1 -ZipPath "$env:USERPROFILE\Downloads\PAL_Tracker_Goalposts_and_Approve_UI_FixLLM.zip"
```

## Enable goalposts + refresh tracker
```powershell
pwsh .\pal\scripts\ps\pal_add_goalposts.ps1
```

## Re-run your doc→yaml test (fixed)
```powershell
python .\pal\scripts\py\run_doc_to_yaml.py README.md openai
```

## Notes
- Colors: grey=todo, amber(in-progress), blue=review (PASS), red=blocked (FAIL), green=done (approved).
- Approve blue items directly from the tracker via **Approve → Done** button.
