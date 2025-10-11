#!/usr/bin/env python3
import json, sys
from pathlib import Path
try:
    import yaml
except Exception:
    print("PyYAML required", file=sys.stderr); sys.exit(2)

PLAN1 = Path("pal/plan/pal_project_plan.yaml")
PLAN2 = Path("project/plans/project_plan_v3.yaml")

GOALPOSTS = {
    "M0": "Unbreakable phone/web control; watchdog + tracker healthy.",
    "P1": "Legacy quarantined; smoke harness + auto-flip stable pipeline.",
    "P2": "Operator UX: color tree, status transitions, desktop approvals.",
    "P3": "Phone/Web approvals: approve from phone; minimal web dashboard; notes captured."
}

def pick_plan():
    if PLAN1.exists(): return PLAN1
    if PLAN2.exists(): return PLAN2
    return PLAN1

def main():
    p = pick_plan()
    data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    changed = []
    for ph in data.get("phases", []):
        pid = str(ph.get("id",""))
        if pid in GOALPOSTS and not ph.get("goalpost"):
            ph["goalpost"] = GOALPOSTS[pid]
            changed.append(pid)
    p.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
    print(json.dumps({"ok": True, "plan": str(p), "changed": changed}))

if __name__ == "__main__":
    main()
