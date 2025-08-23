# --- PA_ROOT_IMPORT ---
import sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
# --- /PA_ROOT_IMPORT ---
import yaml
PLAN = r"project\\plans\\project_plan_v3.yaml"
with open(PLAN,"r",encoding="utf-8") as f: d=yaml.safe_load(f)

p4 = None
for ph in d.get("phases",[]):
    if str(ph.get("name","")).startswith("Phase 4"):
        p4 = ph; break

if p4 is not None:
    steps = p4.setdefault("steps",[])
    def ensure_step(_id, desc):
        if not any(s.get("id")==_id for s in steps):
            steps.append({"id":_id, "status":"in_progress", "description":desc, "items":[]})

    ensure_step("4.1", "Model & Mode UI (OpenAI active; others disabled/visible)")
    ensure_step("4.1.1", "Model probe matrix (parallel): ping status per model; summarize failures for parallel fixes")
    ensure_step("4.1.2", "Capability cataloging: record model capability tags after successful ping")
    # Leave current_step unchanged

with open(PLAN,"w",encoding="utf-8") as f: yaml.safe_dump(d,f,sort_keys=False)
print("[PLAN OK] parallel probe steps ensured (4.1.1, 4.1.2).")
