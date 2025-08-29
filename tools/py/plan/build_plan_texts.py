#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Builds a consistent "id -> {title, desc, status}" map from your plan file.

INPUT (read-only):
  project\plans\project_plan_v3.yaml   (auto-discovered from this script's parents,
                                        or override with --in)

OUTPUT:
  web\pwa\plan_texts.json              # consumed by the PWA
  project\plans\plan_texts_full.yaml   # normalized + naturally sorted list (for review)
"""
import argparse, os, json, re
from pathlib import Path

try:
    import yaml  # pip install pyyaml
except ImportError:
    raise SystemExit("PyYAML missing. pip install pyyaml")

# ---------- locate repo root ----------
def find_repo_root(start: Path) -> Path:
    start = start.resolve()
    for p in [start] + list(start.parents):
        if (p / "project" / "plans" / "project_plan_v3.yaml").exists():
            return p
    # Fallback: 3 levels up (repo_root/tools/py/plan -> repo_root)
    return start.parents[3] if len(start.parents) >= 3 else start

def norm_status(s: str) -> str:
    s = (s or "").strip().lower()
    if s in ("planned","todo","to_do","tbd"): return "planned"
    if s in ("in_progress","in-progress","active","working","running"): return "in_progress"
    if s in ("done","complete","finished"): return "done"
    if s in ("blocked","fail","failed","error"): return "blocked"
    return "planned"

def short(s: str, n: int = 90) -> str:
    s = (s or "").strip()
    return s if len(s) <= n else s[: n - 1] + "…"

def first_text(d: dict) -> str:
    for k in ("text","desc","description","brief","note"):
        v = d.get(k)
        if isinstance(v,str) and v.strip():
            return v.strip()
    return ""

def derive_title(d: dict) -> str:
    t = (d.get("title") or d.get("name") or "").strip()
    if t: return t
    body = first_text(d)
    if body:
        first = re.split(r"[.!?\n]", body, 1)[0]
        return short(first, 80)
    return d.get("id") or "(untitled)"

def id_sort_key(step_id: str):
    toks = []
    for part in str(step_id).replace("-", ".").split("."):
        if part.isdigit(): toks.append((int(part), ""))        # numeric chunk
        else:              toks.append((10_000_000, part.lower()))
    return tuple(toks)

def walk(obj, found):
    if isinstance(obj, dict):
        if "id" in obj: found.append(obj)
        for v in obj.values(): walk(v, found)
    elif isinstance(obj, list):
        for v in obj: walk(v, found)

def main():
    here = Path(__file__).resolve()
    repo = find_repo_root(here)

    ap = argparse.ArgumentParser()
    ap.add_argument("--in",   dest="inp",      default=str(repo / r"project\plans\project_plan_v3.yaml"))
    ap.add_argument("--json", dest="json_out", default=str(repo / r"web\pwa\plan_texts.json"))
    ap.add_argument("--yaml", dest="yaml_out", default=str(repo / r"project\plans\plan_texts_full.yaml"))
    a = ap.parse_args()

    src = Path(a.inp)
    if not src.exists():
        raise SystemExit(f"Plan not found: {src}")

    try:
        doc = yaml.safe_load(src.read_text(encoding="utf-8"))
    except Exception as e:
        raise SystemExit(f"YAML parse failed: {e}")

    steps = []
    walk(doc, steps)
    if not steps:
        raise SystemExit("No steps with 'id' found in the plan.")

    by_id = {}
    for n in steps:
        sid = str(n.get("id") or "").strip()
        if not sid: continue
        rec = {
            "id": sid,
            "title": derive_title(n),
            "desc": first_text(n),
            "status": norm_status(n.get("status")),
        }
        for k in ("items","files","success","tags"):
            if k in n: rec[k] = n[k]
        by_id[sid] = rec   # last wins

    ordered = [by_id[k] for k in sorted(by_id.keys(), key=id_sort_key)]

    out_json = Path(a.json_out); out_json.parent.mkdir(parents=True, exist_ok=True)
    out_yaml = Path(a.yaml_out); out_yaml.parent.mkdir(parents=True, exist_ok=True)

    id_map = { r["id"]: {"title": r["title"], "desc": r["desc"], "status": r["status"]} for r in ordered }
    out_json.write_text(json.dumps(id_map, ensure_ascii=False, indent=2), encoding="utf-8")

    out_yaml.write_text(yaml.safe_dump({"steps": ordered}, sort_keys=False, allow_unicode=True), encoding="utf-8")

    print("Wrote:", out_json)
    print("Wrote:", out_yaml)
    print("Stats:", f"ids={len(ordered)}  repo={repo}")

if __name__ == "__main__":
    main()
