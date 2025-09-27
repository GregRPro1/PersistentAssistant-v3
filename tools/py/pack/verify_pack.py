# tools/py/pack/verify_pack.py
# Verify snapshot pack contains plan, catalog, reporters. Auto-picks latest pack if --in omitted.
from __future__ import annotations
import argparse, zipfile, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
FB   = ROOT / "tmp" / "feedback"

REQUIRED = [
    "plan_snapshot.yaml",
    "tools/tool_catalog.json",
    "tools/tool_catalog.yaml",
    "tools/tool_catalog.md",
    "project_structure/file_manifest.yaml",
    "project_structure/project_structure_snapshot_index.md",
    # insights are optional; if present, verify their presence via a separate flag
]

INSIGHTS = [
    "insights/file_headers.yaml",
    "insights/md_headings.yaml",
    "insights/deep_inventory.yaml",
    "insights/deep_calls.yaml",
    "insights/docstring_report.yaml",
    "insights/duplication_report.yaml",
    "insights/imports.yaml",
    "insights/deep_inventory.dot",
]

def _latest_pack() -> Path | None:
    if not FB.exists(): return None
    cands = list(FB.glob("pack_*.zip")) + list(FB.glob("pack_project_snapshot_*.zip"))
    if not cands: return None
    return max(cands, key=lambda p: p.stat().st_mtime)

def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="pack_in", help="Path to pack zip; if omitted, use latest in tmp/feedback")
    ap.add_argument("--include-meta", action="store_true", help="Print ZIP path and simple meta")
    ap.add_argument("--check-insights", action="store_true", help="Also require insights files")
    args = ap.parse_args(argv)

    pack_path = Path(args.pack_in) if args.pack_in else _latest_pack()
    if not pack_path or not pack_path.exists():
        print("No snapshot pack found.")
        return 2

    req = list(REQUIRED)
    if args.check_insights:
        req.extend(INSIGHTS)

    have = set()
    with zipfile.ZipFile(pack_path, "r") as z:
        for info in z.infolist():
            have.add(info.filename)

    missing = [p for p in req if p not in have]
    for p in req:
        print(f"{p} => {'OK' if p in have else 'MISSING'}")

    print(f"ZIP: {pack_path}")
    return 0 if not missing else 1

if __name__ == "__main__":
    sys.exit(main())
