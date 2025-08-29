# tools/py/plan_step_add.py
# Safe updater for project/plans/project_plan_v3.yaml
# - Backs up with timestamp
# - Finds appropriate container for <id> (prefers siblings of same major prefix)
# - Adds/updates the step (id/title/status/desc)
# - Sorts siblings by id
# - Writes unified diff
# - Verifies via tools/show_next_step.py

from __future__ import annotations
import argparse, os, sys, shutil, time, json, difflib, subprocess, pathlib
from typing import Any, Dict, List, Optional, Tuple

try:
    import yaml  # PyYAML
except Exception as e:
    print("ERROR: PyYAML is required (pip install pyyaml).", file=sys.stderr)
    sys.exit(2)

ROOT = pathlib.Path(__file__).resolve().parents[2]
PLAN = ROOT / "project" / "plans" / "project_plan_v3.yaml"
TMP  = ROOT / "tmp"
RUN  = TMP / "run"
BACKUPS = TMP / "backups"
SHOW_NEXT = ROOT / "tools" / "show_next_step.py"

def ts() -> str:
    return time.strftime("%Y%m%d_%H%M%S")

def read_text(p: pathlib.Path) -> str:
    return p.read_text(encoding="utf-8", errors="replace")

def write_text(p: pathlib.Path, s: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(s, encoding="utf-8")

def load_yaml(p: pathlib.Path) -> Any:
    return yaml.safe_load(read_text(p))

def dump_yaml(data: Any) -> str:
    # Keep keys order as inserted; avoid sorting
    return yaml.dump(data, allow_unicode=True, sort_keys=False)

def walk(parent: Any, path: Tuple = ()) -> List[Tuple[Tuple, Any]]:
    """Yield (path, node) pairs for dicts/lists scalars."""
    out: List[Tuple[Tuple, Any]] = []
    out.append((path, parent))
    if isinstance(parent, dict):
        for k, v in parent.items():
            out.extend(walk(v, path + (("dict", k),)))
    elif isinstance(parent, list):
        for i, v in enumerate(parent):
            out.extend(walk(v, path + (("list", i),)))
    return out

def find_all_step_lists(doc: Any) -> List[Tuple[Tuple, List[Dict[str, Any]], Optional[Dict[str, Any]]]]:
    """
    Return lists that *look like* step collections: list of dicts each with 'id'.
    Also return their parent dict (if any) to allow setting children etc.
    """
    hits: List[Tuple[Tuple, List[Dict[str, Any]], Optional[Dict[str, Any]]]] = []
    for path, node in walk(doc):
        if isinstance(node, list) and node and all(isinstance(x, dict) and "id" in x for x in node):
            # parent dict (if last path segment is ('dict', key))
            parent = None
            if path and path[-1][0] == "list":
                # need to look one level up
                # find container node for this list
                # traverse from doc using path[:-1]
                parent = get_by_path(doc, path[:-1])
            hits.append((path, node, parent if isinstance(parent, dict) else None))
    return hits

def get_by_path(doc: Any, path: Tuple) -> Any:
    cur = doc
    for kind, key in path:
        if kind == "dict":
            cur = cur.get(key) if isinstance(cur, dict) else None
        else:
            idx = int(key)
            if isinstance(cur, list) and 0 <= idx < len(cur):
                cur = cur[idx]
            else:
                return None
    return cur

def find_container_for_id(doc: Any, step_id: str) -> Tuple[List[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """
    Prefer the list that already contains siblings with same major prefix (e.g., '6.4.').
    Else fall back to the first step-like list.
    """
    major = step_id.split(".", 2)
    major_key = ".".join(major[:2]) if len(major) >= 2 else step_id
    hits = find_all_step_lists(doc)
    # Look for an existing sibling list with same major prefix
    def has_same_major(lst: List[Dict[str, Any]]) -> bool:
        for it in lst:
            sid = str(it.get("id", ""))
            if sid.startswith(major_key + ".") or sid == major_key:
                return True
        return False
    for path, lst, parent in hits:
        if has_same_major(lst):
            return (lst, parent)
    # Otherwise pick the first step-like list
    if hits:
        return (hits[0][1], hits[0][2])
    # If nothing found, create a top-level 'steps' list
    if isinstance(doc, dict):
        doc.setdefault("steps", [])
        return (doc["steps"], doc)
    # If doc is not dict, wrap
    new_doc = {"steps": []}
    return (new_doc["steps"], new_doc)

def find_in_list_by_id(lst: List[Dict[str, Any]], step_id: str) -> Optional[Dict[str, Any]]:
    for it in lst:
        if str(it.get("id", "")) == step_id:
            return it
    return None

def normalize_status(s: str) -> str:
    s = (s or "").strip().lower()
    if s in ("planned", "todo"): return "planned"
    if s in ("in_progress", "in-progress", "active", "working"): return "in_progress"
    if s in ("done", "complete", "finished"): return "done"
    if s in ("blocked", "fail", "failed", "error"): return "blocked"
    return "planned"

def sort_by_id(lst: List[Dict[str, Any]]) -> None:
    def key(it: Dict[str, Any]) -> Tuple:
        sid = str(it.get("id", ""))
        # split id into numeric + alpha tokens for natural order
        toks: List[Tuple[int, str]] = []
        for part in sid.replace("-", ".").split("."):
            if part.isdigit():
                toks.append((int(part), ""))
            else:
                # letters like 'a','b','c'
                toks.append((10_000_000, part))
        return tuple(toks)
    lst.sort(key=key)

def run_show_next(step_file_out: pathlib.Path, step_file_err: pathlib.Path) -> None:
    if not SHOW_NEXT.exists():
        write_text(step_file_err, "tools/show_next_step.py not found")
        return
    try:
        res = subprocess.run([sys.executable, str(SHOW_NEXT)], cwd=str(ROOT),
                             capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=20)
        write_text(step_file_out, res.stdout or "")
        write_text(step_file_err, res.stderr or "")
    except Exception as ex:
        write_text(step_file_err, f"show_next_step failed: {ex}")

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", required=True, help="Step ID, e.g. 6.4.c")
    ap.add_argument("--title", required=True, help="Short title")
    ap.add_argument("--status", default="planned", help="planned|in_progress|done|blocked (normalized)")
    ap.add_argument("--desc", default="", help="Optional description")
    ap.add_argument("--set-active", action="store_true", help="Set this step as active_step")
    ap.add_argument("--dry-run", action="store_true", help="Do not write the file; only show diff")
    args = ap.parse_args()

    if not PLAN.exists():
        print(f"ERROR: {PLAN} not found.", file=sys.stderr)
        return 2

    original_text = read_text(PLAN)
    try:
        doc = yaml.safe_load(original_text)
    except Exception as ex:
        print(f"ERROR: YAML parse failed: {ex}", file=sys.stderr)
        return 2

    if not isinstance(doc, dict):
        print("ERROR: Unexpected plan format (not a dict).", file=sys.stderr)
        return 2

    step_list, parent_dict = find_container_for_id(doc, args.id)
    if not isinstance(step_list, list):
        print("ERROR: Could not locate or create a step list.", file=sys.stderr)
        return 2

    tgt = find_in_list_by_id(step_list, args.id)
    status_norm = normalize_status(args.status)

    if tgt is None:
        tgt = {"id": args.id, "title": args.title, "status": status_norm}
        if args.desc.strip():
            tgt["desc"] = args.desc.strip()
        step_list.append(tgt)
        action = "added"
    else:
        # Update in place (minimal changes)
        if args.title.strip():
            tgt["title"] = args.title.strip()
        tgt["status"] = status_norm
        if args.desc.strip():
            tgt["desc"] = args.desc.strip()
        action = "updated"

    # Keep siblings ordered
    sort_by_id(step_list)

    # Optionally set active_step
    if args.set_active:
        doc["active_step"] = args.id

    new_text = dump_yaml(doc)

    # Diff
    RUN.mkdir(parents=True, exist_ok=True)
    diff_path = RUN / f"plan_update_{ts()}.diff"
    diff = difflib.unified_diff(
        original_text.splitlines(keepends=True),
        new_text.splitlines(keepends=True),
        fromfile=str(PLAN),
        tofile=str(PLAN) + " (updated)"
    )
    write_text(diff_path, "".join(diff))

    if args.dry_run:
        print("DRY-RUN: no changes written.")
        print(f"Diff: {diff_path}")
        return 0

    # Backup + write
    BACKUPS.mkdir(parents=True, exist_ok=True)
    backup = BACKUPS / f"project_plan_v3.yaml.bak.{ts()}"
    shutil.copy2(PLAN, backup)
    write_text(PLAN, new_text)

    # Verify with show_next_step
    step_out = RUN / f"show_next_{ts()}.txt"
    step_err = RUN / f"show_next_{ts()}.stderr.txt"
    run_show_next(step_out, step_err)

    # Report
    report = {
        "plan": str(PLAN),
        "backup": str(backup),
        "diff": str(diff_path),
        "action": action,
        "id": args.id,
        "title": args.title,
        "status": status_norm,
        "active_set": bool(args.set_active),
        "verify": {
            "stdout": str(step_out),
            "stderr": str(step_err),
        }
    }
    print(json.dumps(report, indent=2))
    return 0

if __name__ == "__main__":
    sys.exit(main())
