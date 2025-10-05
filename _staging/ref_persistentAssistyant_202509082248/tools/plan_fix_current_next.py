from __future__ import annotations
# --- PA_ROOT_IMPORT ---
import sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
# --- /PA_ROOT_IMPORT ---
import yaml, re, sys
PLAN = r"project\\plans\\project_plan_v3.yaml"

def step_key(step_id:str):
    # normalize like 4, 4.1, 4.1.3 etc to tuple of ints for sorting
    parts=[]
    for p in str(step_id).split("."):
        try: parts.append(int(p))
        except: parts.append(0)
    return tuple(parts)

with open(PLAN,"r",encoding="utf-8") as f:
    d=yaml.safe_load(f)

# Find Phase 4; ensure steps sorted and statuses considered
p4=None
for ph in d.get("phases",[]):
    if str(ph.get("name","")).startswith("Phase 4"):
        p4=ph;break

cur=""; nxt=""
if p4:
    steps = p4.get("steps",[])
    steps.sort(key=lambda s: step_key(s.get("id","0")))
    # current = last with status 'in_progress' else last 'done' in Phase 4/5
    cur_step=None
    for s in steps:
        if s.get("status")=="in_progress":
            cur_step=s
    if not cur_step:
        for s in reversed(steps):
            if s.get("status")=="done":
                cur_step=s; break
    # next = first planned after current
    nxt_step=None
    if cur_step:
        passed=False
        for s in steps:
            if s is cur_step: 
                passed=True; 
                continue
            if passed and s.get("status") in ("planned","in_progress"):
                nxt_step=s; break
    # fallback to Phase 5 if Phase 4 completed
    if not nxt_step:
        for ph in d.get("phases",[]):
            if str(ph.get("name","")).startswith("Phase 5"):
                for s in ph.get("steps",[]):
                    if s.get("status") in ("planned","in_progress"):
                        nxt_step=s; break
                break
    if cur_step:
        cur=f"{cur_step.get('id')} - {cur_step.get('description')} [{cur_step.get('status')}]"
    if nxt_step:
        nxt=f"{nxt_step.get('id')} - {nxt_step.get('description')} [{nxt_step.get('status')}]"

d.setdefault("meta",{})["current_step"]= (cur_step or {}).get("id","")
with open(PLAN,"w",encoding="utf-8") as f:
    yaml.safe_dump(d,f,sort_keys=False)

print("[PLAN OK] current/next reconciled")
print("Current:", cur or "<none>")
print("Next:   ", nxt or "<none>")
