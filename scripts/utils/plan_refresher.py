#!/usr/bin/env python3
from __future__ import annotations
import time, yaml, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PLAN_YAML = ROOT / "pal_project_plan.yaml"
STATE_JSON = ROOT / "_state" / "plan_status.json"

ICON_DONE = "✅"
ICON_ACTIVE = "▶"
ICON_TODO = "•"

def load_plan():
    if PLAN_YAML.exists():
        try:
            with PLAN_YAML.open("r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except Exception:
            return {}
    return {}

def build_tasks(plan: dict):
    plans = plan.get("plans", {}) if isinstance(plan, dict) else {}
    active = str(plan.get("active_plan")) if isinstance(plan.get("active_plan"), (int, str)) else None
    # stable order for 13A..13Z if present, else insertion order
    order = sorted([k for k in plans.keys() if str(k).startswith("13")])
    out = []
    for k in order:
        item = plans.get(k, {}) or {}
        title = item.get("title", str(k))
        status = (item.get("status") or "").lower()
        if status == "complete":
            icon = ICON_DONE
        elif active and str(k) == str(active):
            icon = ICON_ACTIVE
        else:
            icon = ICON_TODO
        out.append(f"{k} – {title} {icon}")
    return out

def write_state(tasks):
    STATE_JSON.parent.mkdir(parents=True, exist_ok=True)
    now = time.time()
    # Preserve existing selected_plan if present to avoid UI confusion (e.g., Phase-R1)
    existing = {}
    if STATE_JSON.exists():
        try:
            existing = json.loads(STATE_JSON.read_text(encoding="utf-8"))
        except Exception:
            existing = {}
    selected = existing.get("selected_plan", "Phase-R1")
    payload = {
        "selected_plan": selected,
        "updated_ts": now,
        "tasks": tasks,
    }
    tmp = STATE_JSON.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(STATE_JSON)

def main(loop: int = 10):
    while True:
        plan = load_plan()
        tasks = build_tasks(plan)
        write_state(tasks)
        time.sleep(loop)

if __name__ == "__main__":
    main(10)
