# PAL Tracker (Desktop, PyQt6)

A minimal desktop tracker for **PAL** (Persistent Assistant Lite).

- Dark mode UI
- Goals panel (top-left), Task tree (left), Details (right)
- Color coding by status (done/in_progress/review/blocked/todo)
- Auto-refresh every 15 seconds from `pal/plan/pal_project_plan.yaml`
- Defaults to the first `in_progress`, else `todo`

## Run

```powershell
# From repo root, recommended inside your venv
pip install -r pal/ui/desktop/requirements.txt
python pal/ui/desktop/pal_tracker.py
# or specify a custom plan path
python pal/ui/desktop/pal_tracker.py pal/plan/pal_project_plan.yaml
```

If PyYAML is unavailable, the app uses a tiny built-in fallback parser for the shipped plan structure.
