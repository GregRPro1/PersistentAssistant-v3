import json, yaml, pathlib
ok = False
try:
    data = json.loads(pathlib.Path("tmp/leb_check.json").read_text(encoding="utf-8"))
    ok = (data.get("ping",{}).get("ok") is True) and (data.get("run",{}).get("ok") is True)
except Exception:
    ok = False

if ok:
    PLAN = pathlib.Path("project/plans/project_plan_v3.yaml")
    d = yaml.safe_load(PLAN.read_text(encoding="utf-8"))
    for ph in d.get("phases", []):
        n = str(ph.get("name",""))
        if n.startswith("Phase 6"):
            for st in ph.get("steps", []):
                if st.get("id") == "6.3.c":
                    st["status"] = "done"
    PLAN.write_text(yaml.safe_dump(d, sort_keys=False), encoding="utf-8")
    print("[PLAN OK] 6.3.c marked done.")
else:
    print("[PLAN NOTE] 6.3.c remains in_progress (LEB checks not fully OK).")
