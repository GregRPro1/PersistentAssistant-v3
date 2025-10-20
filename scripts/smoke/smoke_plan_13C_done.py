#!/usr/bin/env python3
import yaml, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
plan = ROOT / "pal_project_plan.yaml"
trk  = ROOT / "master_project_tracker.yaml"
for p in (plan, trk):
    if not p.exists():
        print(f"[FAIL] missing {p}"); sys.exit(2)
pd = yaml.safe_load(plan.read_text(encoding="utf-8")) or {}
md = yaml.safe_load(trk.read_text(encoding="utf-8")) or {}
ok = (pd.get("plans",{}).get("13C",{}).get("status") == "complete"
      and md.get("milestones",{}).get("PAL-13C",{}).get("state") == "done")
if ok:
    print("[OK] 13C marked complete"); sys.exit(0)
else:
    print("[FAIL] 13C not complete in plan files"); sys.exit(3)
