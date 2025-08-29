# tools/py/inventory/report_index.py
# Emits project_structure_snapshot_index.md from file_manifest.yaml
from __future__ import annotations
import sys, json, yaml, pathlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]  # repo root
OUT_MD = ROOT / "project" / "structure" / "project_structure_snapshot_index.md"
MANIFEST_CANDIDATES = [
    ROOT / "project" / "structure" / "file_manifest.yaml",
    ROOT / "project" / "structure" / "file_manifest.yml",
]

def load_manifest() -> list[dict]:
    for p in MANIFEST_CANDIDATES:
        if p.exists():
            try:
                data = yaml.safe_load(p.read_text(encoding="utf-8"))
            except Exception as e:
                print(f"Manifest read error: {p} -> {e}", file=sys.stderr)
                sys.exit(1)
            # Accept multiple shapes
            if isinstance(data, list):
                return data
            if isinstance(data, dict):
                for k in ("files", "items", "entries", "list", "data"):
                    v = data.get(k)
                    if isinstance(v, list):
                        return v
            print("Manifest is not a list (no files/items/entries/list/data key).", file=sys.stderr)
            sys.exit(1)
    print("Manifest not found.", file=sys.stderr)
    sys.exit(1)

def main() -> int:
    items = load_manifest()
    lines = ["# Project Structure Snapshot (index)", ""]
    for it in items:
        path = it.get("path") or it.get("rel") or it.get("file") or ""
        if not path:
            # skip malformed rows quietly
            continue
        cls_n = len(it.get("classes", [])) if isinstance(it.get("classes"), list) else 0
        fn_n  = len(it.get("functions", [])) if isinstance(it.get("functions"), list) else 0
        loc   = it.get("lines_of_code", 0)
        lines.append(f"- `{path}` — classes:{cls_n} funcs:{fn_n} loc:{loc}")
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "wrote": str(OUT_MD)}, ensure_ascii=False))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

