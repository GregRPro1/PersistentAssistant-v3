#!/usr/bin/env python3
import sys, pathlib, yaml, json
def pick_plan_path():
    p1 = pathlib.Path("pal/plan/pal_project_plan.yaml")
    if p1.exists(): return p1
    p2 = pathlib.Path("project/plans/project_plan_v3.yaml")
    if p2.exists(): return p2
    return p1
def set_status(plan: pathlib.Path, ids, status: str) -> dict:
    data = yaml.safe_load(plan.read_text(encoding="utf-8")) or {}
    found = []
    for ph in data.get("phases", []):
        for t in ph.get("tasks", []):
            if str(t.get("id")) in ids:
                t["status"] = status
                found.append(str(t.get("id")))
    plan.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return {"updated": found, "status": status, "plan": str(plan)}
def main(argv):
    if len(argv) < 3:
        print("usage: pal_mark_status.py <status> <ID1> [ID2 ...]", file=sys.stderr)
        sys.exit(1)
    status = argv[1]
    ids = argv[2:]
    plan = pick_plan_path()
    res = set_status(plan, ids, status)
    print(json.dumps(res))
if __name__ == "__main__":
    main(sys.argv)
