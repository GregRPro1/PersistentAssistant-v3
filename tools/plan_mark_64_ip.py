import yaml, os
PLAN = r"project\\plans\\project_plan_v3.yaml"
try:
    with open(PLAN, "r", encoding="utf-8") as f:
        d = yaml.safe_load(f) or {}
    for ph in d.get("phases", []):
        if str(ph.get("name","")).startswith("Phase 6"):
            for st in ph.get("steps", []):
                if st.get("id") in ("6.4", "6.4a", "6.4-ci"):
                    st["status"] = "in_progress"
    with open(PLAN, "w", encoding="utf-8") as f:
        yaml.safe_dump(d, f, sort_keys=False)
    print("[PLAN OK] 6.4 -> in_progress")
except Exception as e:
    print("[PLAN WARN]", e)
