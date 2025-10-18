# PAL20251013A Consolidated Learnings (A + A-EXT)

## What was achieved
- **Plan selection signal is now reliable** via a sidecar writer in `scripts/tracker/start_tracker_with_plan.py` that updates `_state/plan_status.json` every ~5s.
- **Watchdog UI layout stabilized** by appending CSS directly to `scripts/watchdog/static/style.css` (marker: `/* PAL-UX-APPEND B.3 */`), avoiding template mutations.
- **Tracker launch path standardized** to the wrapper (`scripts/tracker/start_tracker_with_plan.py`) so env (`PAL_PLAN`) and diagnostics are consistent.
- **Python-first smoke tests** added (`scripts/smoke/*.py`), replacing fragile PowerShell smokes for bridge/heartbeat/plan state checks.

## Root-cause fixes captured
- **Dynamic import brittleness** inside `pal_tracker.py` is bypassed for now with the wrapper + sidecar approach; we’ll revisit clean, explicit hooks during the 13B UI work.
- **Pack apply robustness**: avoided “copy to itself” and `Join-Path` array pitfalls; all mutations guarded by `py_compile` before writing to repo files.
- **No more inline Python-in-PS parsing bugs**: code-gen packs keep Python in `.py` files; PowerShell only orchestrates.

## Disciplined process we followed
1. **Define a single milestone**: prove plan selection signal → *done via sidecar & smoke (`smoke_plan_promoted.py`)*.
2. **Close the context with a summary + tag** before starting UI work.
3. **Open PAL20251013B** explicitly for the Tracker Plan Selector & Bridge UI; avoid scope creep here.

## Known gaps (to be addressed in PAL20251013B)
- Tracker UI currently **does not render** the selected plan or task list.
- Bridge JSON (`reports/ops/ops_status.json`) not yet wired to the Tracker UI for heartbeat/URL badges.
- Watchdog ↔ Tracker **log tail mapping** needs to point at `tmp/bridge_tracker.log` for consistent diagnostics.

## Reliable commands (A consolidated)
```powershell
# Start Watchdog
python .\scripts\watchdog\watchdog_ui_basic.py

# Start Tracker with plan sidecar
python .\scripts	racker\start_tracker_with_plan.py

# Smokes
python .\scripts\smoke\smoke_plan_promoted.py        # expect [OK]
python .\scripts\smoke\smoke_bridge_status.py        # prints ops JSON + log tail (if present)
python .\scripts\smoke\smoke_heartbeat_fresh.py      # heartbeat age check (if bridge is running)
```

## Context hygiene
- When the browser gets sluggish or scope changes, **cut to a new sub-context**: `PAL20251013B` for the Plan Selector/Bridge UI.
- Use **Codex toolchain** (`tools/codex/`) for code diffs; all edits must be reviewable patches.
