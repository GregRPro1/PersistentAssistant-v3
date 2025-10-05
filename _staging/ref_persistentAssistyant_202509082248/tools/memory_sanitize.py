# tools/memory_sanitize.py — normalize summary_*.yaml to dict-root
from __future__ import annotations
import pathlib, yaml, datetime

MEM_DIR = pathlib.Path("memory")

def normalize(d, path: pathlib.Path):
    if isinstance(d, dict):
        return d, False
    if isinstance(d, list):
        return {
            "name": path.stem,
            "project": "",
            "date": datetime.datetime.utcnow().isoformat()+"Z",
            "tokens": 0,
            "items": d,
            "tags": [],
            "preview": ""
        }, True
    return {"name": path.stem, "items": [], "tags": [], "preview": ""}, True

def main():
    if not MEM_DIR.exists():
        print("[SAN] memory dir missing; nothing to do.")
        return 0
    changed = 0
    for p in sorted(MEM_DIR.glob("summary_*.yaml")):
        try:
            d = yaml.safe_load(open(p, "r", encoding="utf-8")) or {}
            nd, did = normalize(d, p)
            if did:
                yaml.safe_dump(nd, open(p, "w", encoding="utf-8"), sort_keys=False, allow_unicode=True)
                changed += 1
                print(f"[SAN] normalized {p.name}")
        except Exception as e:
            print(f"[SAN ERR] {p.name}: {e}")
    print(f"[SAN OK] changed={changed}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
