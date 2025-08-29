#!/usr/bin/env python
import sys, json, pathlib, shutil, time
from typing import Any, Dict
try:
    import yaml
except Exception:
    print("PyYAML required (pip install pyyaml)")
    sys.exit(2)

ROOT = pathlib.Path(__file__).resolve().parents[2]
PLAN = ROOT / "project" / "plans" / "project_plan_v3.yaml"

def load() -> Dict[str, Any]:
    if not PLAN.exists():
        print(json.dumps({"ok": False, "error": "plan_missing", "path": str(PLAN)}))
        sys.exit(2)
    try:
        return yaml.safe_load(PLAN.read_text(encoding="utf-8")) or {}
    except Exception as e:
        print(json.dumps({"ok": False, "error": "yaml_load_failed", "detail": str(e)}))
        sys.exit(2)

def save(doc: Dict[str, Any]) -> str:
    bkp = ROOT / "tmp" / "backups"
    bkp.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    bfile = bkp / f"project_plan_v3.yaml.bak.{stamp}"
    shutil.copy2(PLAN, bfile)
    PLAN.write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return str(bfile)

def main(argv):
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", required=True)
    ap.add_argument("--status", required=True)
    args = ap.parse_args()

    doc = load()

    def visit(node: Any) -> bool:
        if isinstance(node, dict):
            nid = node.get("id") or node.get("step_id")
            if nid == args.id:
                node["status"] = args.status
                return True
            return any(visit(v) for v in node.values())
        if isinstance(node, list):
            return any(visit(v) for v in node)
        return False

    if not visit(doc):
        print(json.dumps({"ok": False, "error": "id_not_found", "id": args.id}))
        return 2

    b = save(doc)
    print(json.dumps({"ok": True, "id": args.id, "status": args.status, "backup": b}))
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv))
