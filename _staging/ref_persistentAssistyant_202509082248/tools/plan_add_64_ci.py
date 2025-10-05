import yaml, os, sys
PLAN = r"project\plans\project_plan_v3.yaml"

def ensure_phase_64(d):
    phases = d.setdefault("phases", [])
    p6 = None
    for ph in phases:
        if str(ph.get("name","")).startswith("Phase 6"):
            p6 = ph; break
    if p6 is None:
        p6 = {"name":"Phase 6","steps":[]}
        phases.append(p6)
    steps = p6.setdefault("steps", [])
    ids = {s.get("id") for s in steps}
    def add_step(id_, desc, status="planned"):
        if id_ not in ids:
            steps.append({"id": id_, "description": desc, "status": status})
    add_step("6.4.a", "Add Windows CI workflow (GitHub Actions)", "in_progress")
    add_step("6.4.b", "Run CI smoke (tests minimal) and upload logs", "planned")
    add_step("6.4.c", "Gate on main: CI must pass", "planned")
    return d

with open(PLAN, "r", encoding="utf-8") as f:
    d = yaml.safe_load(f) or {}

d = ensure_phase_64(d)
d.setdefault("meta",{}).update({"current_step":"6.4.a"})

with open(PLAN, "w", encoding="utf-8") as f:
    yaml.safe_dump(d, f, sort_keys=False)

print("[PLAN OK] Phase 6.4 ensured; current_step -> 6.4.a")
