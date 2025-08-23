from __future__ import annotations

# --- PA_ROOT_IMPORT ---
import sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
# --- /PA_ROOT_IMPORT ---

import argparse, json, os, glob, yaml, datetime, pathlib
MEM_DIR = pathlib.Path("memory")

def load_summaries():
    out = []
    if not MEM_DIR.exists():
        return out
    for p in sorted(MEM_DIR.glob("summary_*.yaml")):
        try:
            with open(p, "r", encoding="utf-8") as f:
                d = yaml.safe_load(f) or {}
            out.append({
                "file": str(p),
                "name": d.get("name") or p.stem,
                "project": d.get("project") or "",
                "date": d.get("date") or "",
                "tokens": d.get("tokens") or 0,
                "items": len(d.get("items") or []),
                "tags": d.get("tags") or [],
                "preview": (d.get("preview") or "")[:400],
            })
        except Exception as e:
            out.append({"file": str(p), "name": p.stem, "error": str(e)})
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--as", dest="fmt", choices=["text","json"], default="text")
    args = ap.parse_args()
    rows = load_summaries()
    if args.fmt == "json":
        print(json.dumps(rows, ensure_ascii=False, indent=2))
    else:
        if not rows:
            print("[MEM] no summaries found.")
        for r in rows:
            if "error" in r:
                print(f"- {r['file']}  [ERROR: {r['error']}]")
            else:
                print(f"- {r['file']}  ({r['items']} items, tokens={r['tokens']})  tags={r['tags']}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
