# tools/py/registry/add_tool.py
from __future__ import annotations
import os, sys, argparse, json
from pathlib import Path
from typing import Any, Dict

try:
    import yaml  # type: ignore
except Exception:
    yaml = None  # type: ignore

ROOT = Path(__file__).resolve().parents[3]                 # repo root
OVERLAY = ROOT / "tools" / "tools" / "tool_catalog.overlay.yaml"
# allow tests/CI to point to a temp overlay
OVR = os.getenv("PA_OVERLAY_PATH")
if OVR:
    OVERLAY = Path(OVR).resolve()
    
def _norm_id(kind: str, ref: str) -> str:
    if kind == "endpoint":
        oid = f"endpoint:{ref}"
    elif kind in ("ps", "py"):
        oid = f"{kind}:{ref.replace('\\', '/')}"
    else:
        oid = f"{kind}:{ref}"
    return oid.lower().strip()

def _load_overlay() -> Dict[str, Any]:
    if yaml is None or not OVERLAY.exists():
        return {"overrides": {}}
    try:
        data = yaml.safe_load(OVERLAY.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return {"overrides": {}}
        ov = data.get("overrides")
        if not isinstance(ov, dict):
            data["overrides"] = {}
        return data
    except Exception:
        return {"overrides": {}}

def _save_overlay(obj: Dict[str, Any]) -> None:
    if yaml is None:
        raise SystemExit("PyYAML required to write overlay (pip install pyyaml).")
    OVERLAY.parent.mkdir(parents=True, exist_ok=True)
    OVERLAY.write_text(yaml.safe_dump(obj, sort_keys=False, allow_unicode=True), encoding="utf-8")

def _ensure_unique(kind: str, ref: str) -> None:
    allow_update = os.getenv("PA_ALLOW_TOOL_UPDATE", "").strip().lower() in ("1", "true", "yes", "y")
    overlay = _load_overlay()
    existing = set()
    ov = overlay.get("overrides")
    if isinstance(ov, dict):
        existing.update([k.lower().strip() for k in ov.keys()])

    probe = _norm_id(kind, ref)
    if probe in existing and not allow_update:
        print(json.dumps({
            "ok": False,
            "error": "duplicate_tool",
            "id": probe,
            "overlay": str(OVERLAY)
        }))
        sys.exit(2)

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--kind", required=True, choices=["ps", "py", "endpoint"])
    ap.add_argument("--ref", required=True, help="Path (ps/py) relative to repo, or endpoint rule")
    ap.add_argument("--title", default="")
    ap.add_argument("--description", default="")
    ap.add_argument("--usage", default="")
    ap.add_argument("--tags", default="", help="comma-separated")
    ap.add_argument("--contact", default="", help="email or slack handle")
    args = ap.parse_args()

    _ensure_unique(args.kind, args.ref)

    oid = _norm_id(args.kind, args.ref)
    overlay = _load_overlay()
    overrides = overlay.get("overrides")
    if not isinstance(overrides, dict):
        overrides = {}
        overlay["overrides"] = overrides

    meta: Dict[str, Any] = dict(overrides.get(oid) or {})
    if args.title:
        meta["name"] = args.title
    if args.description:
        meta["description"] = args.description
    if args.usage:
        meta["usage"] = args.usage
    if args.tags:
        meta["tags"] = [t.strip() for t in args.tags.split(",") if t.strip()]
    if args.contact:
        meta["contact"] = args.contact
    meta["source"] = meta.get("source") or "overlay"

    overrides[oid] = meta
    _save_overlay(overlay)
    print(json.dumps({"ok": True, "id": oid, "overlay": str(OVERLAY)}, indent=2))
    return 0

if __name__ == "__main__":
    sys.exit(main())
