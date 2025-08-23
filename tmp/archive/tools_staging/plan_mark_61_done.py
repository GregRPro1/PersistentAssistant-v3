from __future__ import annotations
import yaml
PLAN = r"project\\plans\\project_plan_v3.yaml"
with open(PLAN,"r",encoding="utf-8") as f: d=yaml.safe_load(f)
for ph in d.get("phases",[]):
    if str(ph.get("name","")).startswith("Phase 6"):
        for st in ph.get("steps",[]):
            if st.get("id")=="6.1":
                st["status"]="done"
d.setdefault("meta",{})["current_step"]="6.2"
with open(PLAN,"w",encoding="utf-8") as f: yaml.safe_dump(d,f,sort_keys=False)
print("[PLAN OK] 6.1 -> done; current_step -> 6.2")
