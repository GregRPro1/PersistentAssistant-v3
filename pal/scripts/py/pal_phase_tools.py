#!/usr/bin/env python3
"""
pal_phase_tools.py
Utilities to query/update tasks by phase id in the PAL plan YAML.
Requires PyYAML.
"""
import sys, pathlib, yaml, json

def pick_plan_path() -> pathlib.Path:
    p1 = pathlib.Path("pal/plan/pal_project_plan.yaml")
    if p1.exists(): return p1
    p2 = pathlib.Path("project/plans/project_plan_v3.yaml")
    if p2.exists(): return p2
    return p1

def read_plan(plan: pathlib.Path) -> dict:
    return yaml.safe_load(plan.read_text(encoding="utf-8")) or {}

def write_plan(plan: pathlib.Path, data: dict):
    plan.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")

def list_phase_tasks(phase_id: str) -> list[dict]:
    plan = pick_plan_path()
    data = read_plan(plan)
    tasks = []
    for ph in data.get("phases", []):
        if str(ph.get("id")) == str(phase_id):
            for t in ph.get("tasks", []) or []:
                tasks.append(t)
    return tasks

def set_phase_status(phase_id: str, status: str) -> dict:
    plan = pick_plan_path()
    data = read_plan(plan)
    updated = []
    for ph in data.get("phases", []):
        if str(ph.get("id")) == str(phase_id):
            for t in ph.get("tasks", []) or []:
                t["status"] = status
                updated.append(str(t.get("id")))
    write_plan(pick_plan_path(), data)
    return {"phase": phase_id, "status": status, "updated": updated, "plan": str(pick_plan_path())}

def main(argv):
    if len(argv) < 2:
        print("usage: pal_phase_tools.py <cmd> [args]", file=sys.stderr); sys.exit(1)
    cmd = argv[1]
    if cmd == "list":
        phase = argv[2]
        print(json.dumps({"phase": phase, "tasks": list_phase_tasks(phase)}))
    elif cmd == "set":
        phase, status = argv[2], argv[3]
        print(json.dumps(set_phase_status(phase, status)))
    else:
        print(f"unknown cmd: {cmd}", file=sys.stderr); sys.exit(2)

if __name__ == "__main__":
    main(sys.argv)
