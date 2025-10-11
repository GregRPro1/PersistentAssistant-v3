# PAL — Phone URL in Status Bar + Persisted Approvals

This pack:
- Shows **Phone URL** (LAN or Tunnel) in the **tracker status bar**.
- Prevents smoke watcher from downgrading **done → review**.
- Persists approvals by writing YAML **and** queuing an **auto-commit** via the watchdog.
- Watchdog now publishes **phone.lan** and unified **phone.url** in `reports/ops/ops_status.json` and can handle a `commit_plan` request.

## Apply
```powershell
cd C:\_Repos\PersistentAssistant
pwsh .\scripts\apply_pack.ps1 -ZipPath "$env:USERPROFILE\Downloads\PAL_Statusbar_PhoneURL_and_Persist_Approvals.zip"
```

## Run
```powershell
# Use your normal watchdog entry:
pwsh .\pal\core\health\watchdog.ps1
```

## Manually commit plan (optional)
```powershell
pwsh .\pal\scripts\ps\pal_commit_plan.ps1 -Message "PAL: approvals persisted"
```

**Notes**
- The tracker reads `reports\ops\ops_status.json` and shows: Port, Health, **Phone**, Tunnel, Watcher, Overall.
- Approving a task in the tracker now drops a `commit_plan` request. The watchdog commits the plan and recent smoke artifacts.
- Smoke watcher will only set **review** if status is not **done**.
