#!/usr/bin/env python3
import json, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
state = ROOT / "_state" / "plan_status.json"
state.parent.mkdir(parents=True, exist_ok=True)
payload = {
    "selected_plan": "13D",
    "updated_ts": time.time(),
    "tasks": ["Phone authentication", "Unified launcher (single click/auto-start)"]
}
tmp = state.with_suffix(".json.tmp")
tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
tmp.replace(state)
print("[OK] plan_status updated ->", state)
