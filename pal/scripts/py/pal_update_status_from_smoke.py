#!/usr/bin/env python3
"""
Scan reports/smoke/*.json and flip task status:
  ok==true  -> 'review'
  ok==false -> 'blocked'
Writes a summary JSON.
"""
import json, sys, pathlib, glob
try:
    import yaml  # type: ignore
except Exception:
    print("PyYAML required: pip install PyYAML", file=sys.stderr); sys.exit(2)

def pick_plan_path():
    p1 = pathlib.Path("pal/plan/pal_project_plan.yaml")
    if p1.exists(): return p1
    p2 = pathlib.Path("project/plans/project_plan_v3.yaml")
    if p2.exists(): return p2
    return p1

def load_reports(dirpath: pathlib.Path):
    results = {}
    for p in dirpath.glob("*.json"):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
            tid = str(d.get("test") or d.get("id") or p.stem)
            ok  = bool(d.get("ok"))
            results[tid] = ok
        except Exception:
            pass
    return results

def update_plan(plan: pathlib.Path, results: dict):
    data = yaml.safe_load(plan.read_text(encoding="utf-8")) or {}
    hits = {"review": [], "blocked": [], "skipped": []}
    for ph in data.get("phases", []):
        for t in ph.get("tasks", []):
            tid = str(t.get("id"))
            if tid in results:
                t["status"] = "review" if results[tid] else "blocked"
                hits["review" if results[tid] else "blocked"].append(tid)
            else:
                hits["skipped"].append(tid)
    plan.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return hits

def main():
    smoke_dir = pathlib.Path("reports/smoke")
    if not smoke_dir.exists():
        print(json.dumps({"ok": False, "error": "smoke dir not found"})); sys.exit(2)
    plan = pick_plan_path()
    results = load_reports(smoke_dir)
    hits = update_plan(plan, results)
    print(json.dumps({"ok": True, "plan": str(plan), "results": hits}))

if __name__ == "__main__":
    main()
