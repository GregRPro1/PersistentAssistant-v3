#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, re, time, csv
from pathlib import Path
from typing import Dict, List, Any, Tuple
import yaml

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "plans" / "roadmap"
DUPES_JSON = ROOT / "reports" / "roadmap_duplicates.json"

YAML_PATTERNS = [
    "pal_project_plan.yaml",
    "project/plans/**/*.yaml",
    "plans/**/*.yaml",
    "master_project_tracker.yaml",
    "_context/**/*.yaml",
]
JSON_PATTERNS = [
    "_state/plan_status.json",
    "reports/ops/ops_status.json",
]

CAND_ID_KEYS = ("id","code","key","ref","slug")
CAND_TITLE_KEYS = ("title","name","label","summary")
CAND_STATUS_KEYS = ("status","state","stage")
CAND_NOTES_KEYS = ("notes","desc","description","details")
PHASE_HINT_KEYS = ("phase","phases","roadmap")

def glob_all(root: Path, patterns: List[str]) -> List[Path]:
    out: List[Path] = []
    for pat in patterns:
        for p in root.rglob(pat):
            if p.is_file():
                out.append(p)
    seen = set(); uniq = []
    for p in out:
        rp = p.resolve()
        if rp in seen: continue
        seen.add(rp); uniq.append(p)
    return uniq

def load_yaml(p: Path) -> Any:
    try:
        return yaml.safe_load(p.read_text(encoding="utf-8"))
    except Exception:
        return None

def load_json(p: Path) -> Any:
    try:
        import json
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None

def norm_title(s: str) -> str:
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", " ", s).strip()
    return re.sub(r"\s+", " ", s)

def pick_status(*vals: str) -> str:
    order = ["complete","in-progress","active","pending","todo","deferred","blocked"]
    ranks = {k:i for i,k in enumerate(order)}
    best = None; best_rank = 999
    for v in vals:
        if not v: continue
        v2 = v.lower().strip()
        if v2 in ranks and ranks[v2] < best_rank:
            best = v2; best_rank = ranks[v2]
        elif v2 in ("done","finished","closed"):
            if ranks["complete"] < best_rank:
                best = "complete"; best_rank = ranks["complete"]
        elif v2 in ("wip","current","now","ongoing"):
            if ranks["in-progress"] < best_rank:
                best = "in-progress"; best_rank = ranks["in-progress"]
    return best or "pending"

def extract_nodes(obj: Any, phase_ctx: str|None, source: str) -> List[Dict[str,Any]]:
    items: List[Dict[str,Any]] = []

    def capture(d: Dict[str,Any], phase_hint: str|None):
        cid = None
        for k in CAND_ID_KEYS:
            if isinstance(d.get(k), (str,int)):
                cid = str(d[k]); break
        title = None
        for k in CAND_TITLE_KEYS:
            if isinstance(d.get(k), str) and d[k].strip():
                title = d[k].strip(); break
        if not (cid or title):
            return None
        status = None
        for k in CAND_STATUS_KEYS:
            if isinstance(d.get(k), str) and d[k].strip():
                status = d[k].strip(); break
        notes = None
        for k in CAND_NOTES_KEYS:
            if isinstance(d.get(k), str) and d[k].strip():
                notes = d[k].strip(); break
        return {
            "id": cid or title,
            "title": title or cid or "Untitled",
            "status": pick_status(status) if status else "pending",
            "notes": notes,
            "phase": phase_hint or "R1",
            "source": source,
        }

    def walk(x: Any, phase_hint: str|None):
        if isinstance(x, dict):
            ph = phase_hint
            for k in PHASE_HINT_KEYS:
                if k in x and isinstance(x[k], (str, int)):
                    ph = str(x[k])
            cap = capture(x, ph)
            if cap:
                items.append(cap)
            for v in x.values():
                walk(v, ph)
        elif isinstance(x, list):
            for v in x:
                walk(v, phase_hint)

    walk(obj, phase_ctx)
    return items

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--active", default=None, help="Force-set active item id (e.g., 13D or PAL-13D)")
    args = ap.parse_args()

    yaml_files = glob_all(ROOT, YAML_PATTERNS)
    json_files = glob_all(ROOT, JSON_PATTERNS)

    raw: List[Dict[str,Any]] = []
    for p in yaml_files:
        data = load_yaml(p)
        if data is None: 
            continue
        raw.extend(extract_nodes(data, None, p.as_posix()))

    active_hint = None
    for p in json_files:
        d = load_json(p)
        if isinstance(d, dict) and d.get("selected_plan"):
            active_hint = str(d["selected_plan"]); break
    if args.active: active_hint = args.active

    buckets: Dict[str,List[Dict[str,Any]]] = {}
    for it in raw:
        key = norm_title(it.get("title") or it.get("id") or "")
        if not key: 
            continue
        buckets.setdefault(key, []).append(it)

    merged: List[Dict[str,Any]] = []
    for key, group in buckets.items():
        title = max(group, key=lambda x: len(x.get("title",""))).get("title","Untitled")
        cand_ids = [g["id"] for g in group if g.get("id")]
        cid = cand_ids[0] if cand_ids else title
        status = pick_status(*[g.get("status") for g in group])
        phase = next((g.get("phase") for g in group if g.get("phase")), "R1")
        notes = " | ".join([g.get("notes","") for g in group if g.get("notes")]) or "TBD – description"
        sources = sorted(set([g.get("source") for g in group if g.get("source")]))
        merged.append({
            "id": cid, "title": title, "phase": phase, "status": status,
            "description": notes,
            "deliverables": ["TBD – artifacts/endpoints/scripts"],
            "success_criteria": ["TBD – smoke tests/metrics/UI states"],
            "signoff_checklist": ["TBD – reviewer OK, PR merged, tag created"],
            "sources": sources,
            "active": (str(cid) == str(active_hint)),
        })

    merged.sort(key=lambda x: (str(x.get("phase","R1")), x.get("title","")))

    OUT_DIR = ROOT / "plans" / "roadmap"
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    consolidated_path = OUT_DIR / "consolidated_roadmap.yaml"
    summary_csv = OUT_DIR / "roadmap_summary.csv"
    report_md = OUT_DIR / "roadmap_report.md"
    dupes_json = ROOT / "reports" / "roadmap_duplicates.json"

    with consolidated_path.open("w", encoding="utf-8") as f:
        yaml.safe_dump({"generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                        "active": active_hint, "items": merged}, f, sort_keys=False, allow_unicode=True)

    with summary_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["id","title","phase","status","active","sources"])
        for it in merged:
            w.writerow([it["id"], it["title"], it["phase"], it["status"], it["active"], "; ".join(it["sources"])])

    totals = {"complete":0,"in-progress":0,"active":0,"pending":0,"deferred":0,"blocked":0}
    for it in merged:
        s = it["status"]
        if s in totals: totals[s]+=1
    with report_md.open("w", encoding="utf-8") as f:
        f.write("# Roadmap Report\n\n")
        f.write(f"Generated: {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}\nActive: {active_hint}\n\n")
        f.write("## Totals\n" + "\n".join([f"- {k}: {v}" for k,v in totals.items()]) + "\n\n")
        f.write("## Active / In-Progress\n")
        for it in merged:
            if it["active"] or it["status"] in ("active","in-progress"):
                f.write(f"- {it['id']}: {it['title']}\n")
        f.write("\n## Completed\n")
        for it in merged:
            if it["status"] == "complete":
                f.write(f"- {it['id']}: {it['title']}\n")
        f.write("\n## Pending\n")
        for it in merged:
            if it["status"] in ("pending","todo"):
                f.write(f"- {it['id']}: {it['title']}\n")
        f.write("\n## Deferred/Blocked\n")
        for it in merged:
            if it["status"] in ("deferred","blocked"):
                f.write(f"- {it['id']}: {it['title']}\n")

    with dupes_json.open("w", encoding="utf-8") as f:
        json.dump({k:[{"id":g.get("id"),"title":g.get("title"),"status":g.get("status"),"source":g.get("source")} for g in group]
                   for k,group in buckets.items()}, f, indent=2)

    print(f"[OK] consolidated -> {consolidated_path}")
    print(f"[OK] summary      -> {summary_csv}")
    print(f"[OK] report       -> {report_md}")
    print(f"[OK] duplicates   -> {dupes_json}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
