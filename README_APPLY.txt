# PAL — Watchdog Orchestration + Tracker Status Bar + P4 Scaffold

This pack wires the **watchdog** to orchestrate key components and publish a unified ops status to
`reports/ops/ops_status.json`. The tracker reads it and shows **red/green lights** and the **tunnel URL**.

Also includes a **P4 scaffold** (telemetry + harvest) and smoke tests.

## Apply
```powershell
cd C:\_Repos\PersistentAssistant
pwsh .\scripts\apply_pack.ps1 -ZipPath "$env:USERPROFILE\Downloads\PAL_Watchdog_Orchestration_Tracker_Statusbar_P4.zip"
```

## Start watchdog (one terminal)
```powershell
# Edit config if needed: pal\config\pal_watchdog.json
pwsh .\pal\core\health\watchdog.ps1
```

## What the status bar shows
- **Port <n>**: green if TCP connect succeeds.
- **Health**: green if GET /healthz returns 2xx/3xx.
- **Tunnel**: shows current URL from `reports/ops/tunnel_url.txt` (green if present).
- **Watcher**: green when smoke watcher heartbeat is fresh.
- **Overall**: done/total and time.

## P4 (Telemetry & Harvest) scaffold
- `pal/telemetry/logger.py` -> logs cost/time per task/PR to `reports/telemetry` (`events.jsonl`, `events.csv`)
- `pal/telemetry/harvest.py` -> legacy import stub
- Smokes: `pal/tests/smoke/PAL-030.ps1`, `PAL-031.ps1`

Run P4 smokes:
```powershell
pwsh .\pal\scripts\ps\gen_smoke_for_phase.ps1 -Phase P4
pwsh .\pal\scripts\ps\run_smoke_phase.ps1 -Phase P4
```

The tracker auto-refreshes every 10s to reflect watchdog status and plan changes.
