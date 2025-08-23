# --- PA_ROOT_IMPORT ---
import sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
# --- /PA_ROOT_IMPORT ---
import yaml, re
PLAN = r"project\\plans\\project_plan_v3.yaml"
with open(PLAN,"r",encoding="utf-8") as f: d=yaml.safe_load(f)
# Find Phase 4
p4 = None
for ph in d.get("phases",[]):
    if str(ph.get("name","")).startswith("Phase 4"):
        p4 = ph; break
if p4 is not None:
    steps = p4.setdefault("steps",[])
    # Only add if not present
    if not any(s.get("id")=="4.0R" for s in steps):
        steps.insert(0, {
            "id": "4.0R",
            "status": "done",
            "description": "Reflection Gate: verify existing GUI capability and handlers before any UI change",
            "items": [
              {"title":"deep_inventory refreshed","status":"done"},
              {"title":"reflection_report.yaml created","status":"done"},
              {"title":"pack_reflection created","status":"done"}
            ]
        })
with open(PLAN,"w",encoding="utf-8") as f: yaml.safe_dump(d,f,sort_keys=False)
print("[PLAN OK] Inserted 4.0R (done).")
