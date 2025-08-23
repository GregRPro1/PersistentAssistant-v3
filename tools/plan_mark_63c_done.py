import yaml, pathlib
PLAN = pathlib.Path("project/plans/project_plan_v3.yaml")
d = yaml.safe_load(PLAN.read_text(encoding="utf-8"))
for ph in d.get("phases", []):
    if str(ph.get("name","")).startswith("Phase 6"):
        for st in ph.get("steps", []):
            if st.get("id") in ("6.3.c","6.3c","6.3C"):
                st["status"] = "done"
d.setdefault("meta",{}).update({"current_step":"6.3.d"})
PLAN.write_text(yaml.safe_dump(d, sort_keys=False), encoding="utf-8")
print("[PLAN OK] 6.3.c -> done; current_step -> 6.3.d")
