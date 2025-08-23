import yaml, pathlib, datetime
PLAN = pathlib.Path("project/plans/project_plan_v3.yaml")
if not PLAN.exists():
    print("[PLAN] not found:", PLAN); raise SystemExit(0)

with open(PLAN,"r",encoding="utf-8") as f:
    d = yaml.safe_load(f) or {}

def find_phase(d, prefix):
    for ph in d.get("phases",[]):
        if str(ph.get("name","")).startswith(prefix):
            return ph
    return None

p6 = find_phase(d,"Phase 6")
if p6:
    for st in p6.get("steps",[]):
        if st.get("id") == "6.4":
            st["status"] = st.get("status") or "in_progress"

p7 = find_phase(d,"Phase 7")
if not p7:
    p7 = {"name":"Phase 7 — Phone/PWA Remote Control","status":"planned","steps":[]}
    d.setdefault("phases",[]).append(p7)

ids = { s.get("id") for s in p7.get("steps",[]) }
def add_step(i, desc, status="planned"):
    if i not in ids:
        p7.setdefault("steps",[]).append({"id":i,"description":desc,"status":status})

add_step("7.3","Phone Digest microservice (LAN-only) with token header","in_progress")
add_step("7.4","PWA shell hits /phone/digest and renders cards","planned")
add_step("7.5","Action buttons (Approve/Reject Next Pack) with audit log","planned")

with open(PLAN,"w",encoding="utf-8") as f:
    yaml.safe_dump(d,f,sort_keys=False)
print("[PLAN OK] 6.4 in_progress; 7.3..7.5 ensured.")
