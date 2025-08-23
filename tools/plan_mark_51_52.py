from __future__ import annotations
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
    nm = str(ph.get("name",""))
    if nm.startswith("Phase 5"):
        for st in ph.get("steps",[]):
            if st.get("id")=="5.1": st["status"]="done"
            if st.get("id")=="5.2" and st.get("status")=="planned": st["status"]="in_progress"
d.setdefault("meta",{})["current_step"]="5.2"
with open(PLAN,"w",encoding="utf-8") as f: yaml.safe_dump(d,f,sort_keys=False)
print("[PLAN OK] 5.1 -> done; 5.2 -> in_progress")
