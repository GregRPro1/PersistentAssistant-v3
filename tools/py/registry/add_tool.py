# tools/py/registry/add_tool.py
from __future__ import annotations
import os, sys, pathlib, argparse, json
from typing import Any, Dict

# Optional; only needed for writing the overlay
try:
    import yaml  # type: ignore
except Exception:
    yaml = None  # type: ignore

ROOT = pathlib.Path(__file__).resolve().parents[3]
OVERLAY = ROOT / "tools" / "tools" / "tool_catalog.overlay.yaml"
OVR = os.environ.get("PA_OVERLAY_PATH")
if OVR:
    OVERLAY = pathlib.Path(OVR).resolve()

def load_overlay() -> Dict[str, Any]:
    if yaml is None or not OVERLAY.exists():
        return {"overrides": {}}
    try:
        data = yaml.safe_load(OVERLAY.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return {"overrides": {}}
        data.setdefault("overrides", {})
        return data
    except Exception:
        return {"overrides": {}}

def save_overlay(obj: Dict[str, Any]) -> None:
    if yaml is None:
        raise SystemExit("PyYAML required to write overlay (pip install pyyaml).")
    OVERLAY.parent.mkdir(parents=True, exist_ok=True)
    OVERLAY.write_text(
        yaml.safe_dump(obj, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )

def norm_id(kind: str, ref: str) -> str:
    if kind == "endpoint":
        return "endpoint:{}".format(ref)
    if kind in ("ps", "py"):
        return "{}:{}".format(kind, ref.replace("\\", "/"))
    return "{}:{}".format(kind, ref)

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

    allow_update = os.environ.get("PA_ALLOW_TOOL_UPDATE", "") == "1"
    oid = norm_id(args.kind, args.ref)

    overlay = load_overlay()
    overrides = overlay.get("overrides")
    if not isinstance(overrides, dict):
        overrides = {}
        overlay["overrides"] = overrides

    # Inline duplicate guard (case-insensitive) — respect PA_OVERLAY_PATH
    existing_ids = {str(k).lower().strip() for k in overrides.keys()}
    if (oid.lower().strip() in existing_ids) and (not allow_update):
        print(json.dumps({
            "ok": False,
            "error": "duplicate_tool",
            "id": oid,
            "overlay": str(OVERLAY)
        }))
        sys.exit(2)

    meta: Dict[str, Any] = dict(overrides.get(oid) or {})
    if args.title:       meta["name"] = args.title
    if args.description: meta["description"] = args.description
    if args.usage:       meta["usage"] = args.usage
    if args.tags:        meta["tags"] = [t.strip() for t in args.tags.split(",") if t.strip()]
    if args.contact:     meta["contact"] = args.contact
    meta["source"] = meta.get("source") or "overlay"

    overrides[oid] = meta
    overlay["overrides"] = overrides
    save_overlay(overlay)
    print(json.dumps({"ok": True, "id": oid, "overlay": str(OVERLAY)}, indent=2))
    return 0

if __name__ == "__main__":
    sys.exit(main())
