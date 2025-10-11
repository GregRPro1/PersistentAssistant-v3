#!/usr/bin/env python3
import sys, pathlib, yaml, json
def pick_plan_path():
    p1 = pathlib.Path("pal/plan/pal_project_plan.yaml")
    if p1.exists(): return p1
    p2 = pathlib.Path("project/plans/project_plan_v3.yaml")
    if p2.exists(): return p2
    return p1
def mark_done(plan: pathlib.Path, task_id: str) -> bool:
    if not plan.exists():
        print(f"Plan not found: {plan}", file=sys.stderr); return False
    data = yaml.safe_load(plan.read_text(encoding="utf-8")) or {}
    hit = False
    for ph in data.get("phases", []):
        for t in ph.get("tasks", []):
            if str(t.get("id")) == str(task_id):
                t["status"] = "done"; hit = True
    if not hit:
        print(f"Task id not found: {task_id}", file=sys.stderr); return False
    plan.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return True
def main():
    if len(sys.argv) < 2:
        print("usage: pal_mark_done.py <TASK_ID>", file=sys.stderr); sys.exit(1)
    task_id = sys.argv[1]; plan = pick_plan_path()
    ok = mark_done(plan, task_id)
    print(json.dumps({"ok": bool(ok), "task": task_id, "plan": str(plan)}))
    sys.exit(0 if ok else 2)
if __name__ == "__main__": main()
