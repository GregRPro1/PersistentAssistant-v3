#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, os, re, time, csv
from pathlib import Path
from typing import Dict, List, Any, Tuple
import yaml

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "plans" / "roadmap"
DUPES_JSON = ROOT / "reports" / "roadmap_duplicates.json"

# File patterns to scan
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
MD_PATTERNS = [
    "_context/**/*.md",
]

def glob_files(root: Path, patterns: List[str]) -> List[Path]:
    out: List[Path] = []
    for pat in patterns:
        for p in root.rglob(pat):
            if p.is_file():
                out.append(p)
    # De-dup while preserving order
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
    s = re.sub(r"\b(pal|plan|phase|supervisor|bridge|ui|dashboard)\b", "", s).strip()
    s = re.sub(r"\s+", " ", s)
    return s

def pick_status(*vals: str) -> str:
    # choose the "strongest" status seen across sources
    order = ["complete","in-progress","active","pending","todo","deferred","blocked"]
    ranks = {k:i for i,k in enumerate(order)}
    best = None; best_rank = 999
    for v in vals:
        if not v: continue
        v2 = v.lower().strip()
        if v2 in ranks and ranks[v2] < best_rank:
            best = v2; best_rank = ranks[v2]
        elif v2 in ("done","finished","closed"):  # map to complete
            if ranks["complete"] < best_rank:
                best = "complete"; best_rank = ranks["complete"]
        elif v2 in ("wip","current","now"):  # map to in-progress
            if ranks["in-progress"] < best_rank:
                best = "in-progress"; best_rank = ranks["in-progress"]
    return best or "pending"

def extract_items_from_yaml(data: Any, source: str) -> List[Dict[str,Any]]:
    items: List[Dict[str,Any]] = []
    if not isinstance(data, dict):
        return items
    # common schema variants
    # A) pal_project_plan: { plans: { '13A': {title,status,notes}, ... }, active_plan: ... }
    plans = data.get("plans")
    if isinstance(plans, dict):
        for k, v in plans.items():
            if not isinstance(v, dict): 
                continue
            items.append({
                "id": str(k),
                "title": v.get("title", str(k)),
                "status": (v.get("status") or "").lower() or "pending",
                "notes": v.get("notes"),
                "phase": data.get("phase") or data.get("active_phase"),
                "source": source,
            })
    # B) project_plan_v3: nested phases -> groups -> items
    for key in ("phases","roadmap","phase"):
        if key in data and isinstance(data[key], dict):
            for ph_id, ph_obj in data[key].items():
                # areas/groups
                for gk in ("areas","groups","streams","tracks","sections"):
                    if isinstance(ph_obj, dict) and gk in ph_obj and isinstance(ph_obj[gk], (list,dict)):
                        entries = ph_obj[gk]
                        if isinstance(entries, dict):
                            entries = list(entries.values())
                        for entry in entries:
                            if isinstance(entry, dict):
                                # entry can itself have items
                                if "items" in entry and isinstance(entry["items"], list):
                                    for it in entry["items"]:
                                        if not isinstance(it, dict): 
                                            continue
                                        items.append({
                                            "id": str(it.get("id") or it.get("code") or it.get("name") or it.get("title") or "item"),
                                            "title": str(it.get("title") or it.get("name") or it.get("id") or "Untitled"),
                                            "status": (it.get("status") or "").lower() or "pending",
                                            "notes": it.get("notes"),
                                            "phase": ph_id,
                                            "source": source,
                                        })
                                else:
                                    # leaf entry is itself an item
                                    items.append({
                                        "id": str(entry.get("id") or entry.get("code") or entry.get("name") or entry.get("title") or "item"),
                                        "title": str(entry.get("title") or entry.get("name") or entry.get("id") or "Untitled"),
                                        "status": (entry.get("status") or "").lower() or "pending",
                                        "notes": entry.get("notes"),
                                        "phase": ph_id,
                                        "source": source,
                                    })
    # C) master tracker milestones
    if "milestones" in data and isinstance(data["milestones"], dict):
        for mk, mv in data["milestones"].items():
            if isinstance(mv, dict):
                items.append({
                    "id": str(mk),
                    "title": mv.get("name", str(mk)),
                    "status": (mv.get("state") or "").lower() or "pending",
                    "notes": "; ".join([f"{k}:{v}" for k,v in mv.items() if k not in ("name","state")]) if mv else None,
                    "phase": data.get("phase"),
                    "source": source,
                })
    return items

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--include-context", action="store_true", help="Include context markdown in note extraction")
    ap.add_argument("--min-phase", default=None, help="Filter minimal phase id prefix (e.g., R1)")
    ap.add_argument("--active", default=None, help="Force-set currently active item id (e.g., 13D)")
    args = ap.parse_args()

    yaml_files = glob_files(ROOT, YAML_PATTERNS)
    json_files = glob_files(ROOT, JSON_PATTERNS)
    md_files = glob_files(ROOT, MD_PATTERNS) if args.include_context else []

    # Load & extract
    raw_items: List[Dict[str,Any]] = []
    for p in yaml_files:
        data = load_yaml(p)
        if data is None: 
            continue
        raw_items.extend(extract_items_from_yaml(data, p.as_posix()))

    # Pull active hint from state
    active_hint = None
    for p in json_files:
        d = load_json(p)
        if isinstance(d, dict) and d.get("selected_plan"):
            active_hint = str(d["selected_plan"])
            break
    if args.active:
        active_hint = args.active

    # Normalize + merge duplicates
    merged: Dict[str, Dict[str,Any]] = {}
    dupe_buckets: Dict[str, List[Dict[str,Any]]] = {}

    for it in raw_items:
        title = it.get("title") or it.get("id") or "Untitled"
        key = norm_title(title)
        bucket = dupe_buckets.setdefault(key, [])
        bucket.append(it)

    for key, bucket in dupe_buckets.items():
        # combine
        title = max(bucket, key=lambda x: len(x.get("title",""))).get("title","Untitled")
        # prefer an id that looks structured (e.g., 13A, PAL-13C, R1-SUP-01)
        cand_ids = [b.get("id") for b in bucket if b.get("id")]
        cand_ids_sorted = sorted(cand_ids, key=lambda s: (0 if isinstance(s,str) and (s.startswith("13") or s.startswith("PAL-")) else 1, len(str(s))))
        cid = str(cand_ids_sorted[0]) if cand_ids_sorted else title
        statuses = [b.get("status") for b in bucket if b.get("status")]
        status = pick_status(*statuses)
        notes = " | ".join([b.get("notes","") for b in bucket if b.get("notes")] ) or None
        phase = next((b.get("phase") for b in bucket if b.get("phase")), None)
        sources = [b.get("source") for b in bucket if b.get("source")]

        merged[key] = {
            "id": cid,
            "title": title,
            "phase": phase or "R1",
            "category": None,
            "status": status,
            "description": notes or "TBD – add one-sentence problem/goal summary.",
            "deliverables": ["TBD – list artifacts, endpoints, scripts, or UI changes."],
            "success_criteria": ["TBD – objective checks (smoke tests, endpoints, UI states)."],
            "signoff_checklist": ["TBD – reviewer verifies deliverables & criteria, commits tagged."],
            "sources": sources,
        }

    # Prepare outputs
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    consolidated_path = OUT_DIR / "consolidated_roadmap.yaml"
    summary_csv = OUT_DIR / "roadmap_summary.csv"
    report_md = OUT_DIR / "roadmap_report.md"

    # Sort by phase then title
    items_sorted = sorted(merged.values(), key=lambda x: (str(x.get("phase","R1")), x.get("title","")))

    # Inject active flag
    for it in items_sorted:
        it["active"] = (str(it.get("id")) == str(active_hint))

    import yaml as _yaml
    consolidated = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "active": active_hint,
        "items": items_sorted,
    }
    consolidated_path.write_text(_yaml.safe_dump(consolidated, sort_keys=False, allow_unicode=True), encoding="utf-8")

    # CSV
    with summary_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id","title","phase","status","active","category"])
        for it in items_sorted:
            w.writerow([it["id"], it["title"], it["phase"], it["status"], it["active"], it.get("category") or ""])

    # Report
    done = [i for i in items_sorted if i["status"] == "complete"]
    active = [i for i in items_sorted if i["active"] or i["status"] in ("in-progress","active")]
    pending = [i for i in items_sorted if i["status"] in ("pending","todo")]
    deferred = [i for i in items_sorted if i["status"] in ("deferred","blocked")]

    report = []
    report.append(f"# Roadmap Report\n\nGenerated: {consolidated['generated_at']}\nActive: {active_hint}\n")
    report.append(f"## Totals\n- Items: {len(items_sorted)}\n- Complete: {len(done)}\n- Active: {len(active)}\n- Pending: {len(pending)}\n- Deferred/Blocked: {len(deferred)}\n")
    report.append("## Active / In-Progress\n" + "\n".join([f"- {i['id']}: {i['title']}" for i in active]) + "\n")
    report.append("## Completed\n" + "\n".join([f"- {i['id']}: {i['title']}" for i in done]) + "\n")
    report.append("## Pending\n" + "\n".join([f"- {i['id']}: {i['title']}" for i in pending]) + "\n")
    report_md.write_text("\n".join(report), encoding="utf-8")

    # Duplicates detail
    DUPES_JSON.parent.mkdir(parents=True, exist_ok=True)
    DUPES_JSON.write_text(json.dumps({k:[{"id":b.get("id"),"title":b.get("title"),"status":b.get("status"),"source":b.get("source")} for b in v] for k,v in dupe_buckets.items()}, indent=2), encoding="utf-8")

    print(f"[OK] consolidated -> {consolidated_path}")
    print(f"[OK] summary      -> {summary_csv}")
    print(f"[OK] report       -> {report_md}")
    print(f"[OK] duplicates   -> {DUPES_JSON}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
