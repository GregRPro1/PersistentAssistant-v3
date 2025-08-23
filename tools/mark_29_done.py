# --- PA_ROOT_IMPORT ---
import sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
# --- /PA_ROOT_IMPORT ---
import yaml
PLAN = r"project\\plans\\project_plan_v3.yaml"
with open(PLAN,"r",encoding="utf-8") as f: d=yaml.safe_load(f)
for ph in d.get("phases",[]):
    if str(ph.get("name","")).startswith("Phase 2"):
        for st in ph.get("steps",[]):
            if st.get("id")=="2.9": st["status"]="done"
d.setdefault("meta",{}).update({"current_step":"3.8"})
with open(PLAN,"w",encoding="utf-8") as f: yaml.safe_dump(d,f,sort_keys=False)
print("[PLAN OK] 2.9 -> done; current_step -> 3.8")
