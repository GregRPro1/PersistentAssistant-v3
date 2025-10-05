# --- PA_ROOT_IMPORT ---
import sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
# --- /PA_ROOT_IMPORT ---
import yaml, sys
PLAN = r"project\\plans\\project_plan_v3.yaml"

NEW_STEPS = [
  {
    "id": "2.8",
    "status": "done",
    "description": "Deep inventory + dependency audit in place",
    "items": [
      {"title":"tools/deep_inventory.py generates reports", "status":"done"},
      {"title":"Reports present: deep_inventory, deep_calls, docstring, imports, duplication", "status":"done"}
    ]
  },
  {
    "id": "2.9",
    "status": "in_progress",
    "description": "Snapshot-aware safe replace (use existing tools/safe_replace.py + get_expected_sha.py)",
    "items": [
      {"title":"tools/get_expected_sha.py created", "status":"done"},
      {"title":"(optional) git pre-commit regenerates deep inventory", "status":"planned"}
    ]
  }
]

def ensure_steps(d):
    # find Phase 2 block
    phases = d.get("phases", [])
    phase2 = None
    for ph in phases:
        if str(ph.get("name","")).strip().startswith("Phase 2"):
            phase2 = ph; break
    if not phase2:
        raise SystemExit("[PLAN ERROR] Could not find Phase 2 in plan.")
    steps = phase2.setdefault("steps", [])
    # upsert by id
    by_id = { s.get("id"): s for s in steps }
    changed = False
    for ns in NEW_STEPS:
        sid = ns["id"]
        if sid in by_id:
            # merge status/description/items conservatively
            tgt = by_id[sid]
            tgt["status"] = ns["status"]
            tgt["description"] = ns["description"]
            tgt["items"] = ns["items"]
        else:
            steps.append(ns)
        changed = True
    # sort by numeric step id
    def key(s):
        a,b = s["id"].split(".")
        try: return (int(a), float(b))
        except: return (9999, 9999.0)
    steps.sort(key=key)
    return changed

def main():
    with open(PLAN,"r",encoding="utf-8") as f:
        d = yaml.safe_load(f)
    changed = ensure_steps(d)
    # set current_step to 2.9 to keep us focused
    d.setdefault("meta", {}).update({"current_step": "2.9"})
    with open(PLAN,"w",encoding="utf-8") as f:
        yaml.safe_dump(d, f, sort_keys=False)
    print("[PLAN UPDATED] Added/updated 2.8 and 2.9; current_step=2.9")
if __name__=="__main__":
    main()
