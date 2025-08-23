import yaml
PLAN = r"project\plans\project_plan_v3.yaml"
with open(PLAN,"r",encoding="utf-8") as f: d=yaml.safe_load(f)
for ph in d.get("phases",[]):
    if str(ph.get("name","")).startswith("Phase 6"):
        for st in ph.get("steps",[]):
            if st.get("id") in ("6.3","6.3.a","6.3.b"):
                st["status"]="done"
        # ensure a step 6.3.c exists and is in_progress
        if not any(s.get("id")=="6.3.c" for s in ph.get("steps",[])):
            ph["steps"].append({"id":"6.3.c","status":"in_progress","description":"Wire Run tab to LEB (GUI verified)"})
with open(PLAN,"w",encoding="utf-8") as f: yaml.safe_dump(d,f,sort_keys=False)
print("[PLAN OK] 6.3.c -> in_progress")
