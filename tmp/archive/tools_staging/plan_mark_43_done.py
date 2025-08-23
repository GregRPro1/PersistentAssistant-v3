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
    if str(ph.get("name","")).startswith("Phase 4"):
        for st in ph.get("steps",[]):
            if st.get("id")=="4.3":
                st["status"]="done"
with open(PLAN,"w",encoding="utf-8") as f: yaml.safe_dump(d,f,sort_keys=False)
print("[PLAN OK] 4.3 marked done.")
