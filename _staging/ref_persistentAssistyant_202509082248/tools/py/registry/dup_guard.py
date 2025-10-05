# tools/py/registry/dup_guard.py
from __future__ import annotations
import sys, os
from pathlib import Path

try:
    import yaml  # type: ignore
except Exception:
    yaml = None

ROOT = Path(__file__).resolve().parents[3]
OVERLAY = ROOT / "tools" / "tools" / "tool_catalog.overlay.yaml"

def _norm(s: str) -> str:
    return (s or "").strip().replace("\\", "/").lower()

def _load_overlay():
    if not OVERLAY.exists() or yaml is None:
        return {}
    try:
        data = yaml.safe_load(OVERLAY.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}

def ensure_unique(kind: str, ref: str) -> None:
    """
    Exit(2) if an entry with same (kind, ref) already exists.
    Supports both:
      - dict with "overrides": {"py:tools/py/foo.py": {...}}
      - list of {kind, ref, ...} (legacy)
    Set PA_ALLOW_TOOL_UPDATE=1 to allow overwriting instead of exiting.
    """
    allow_update = os.getenv("PA_ALLOW_TOOL_UPDATE", "").strip().lower() in ("1", "true", "yes", "y")
    overlay = _load_overlay()

    # Gather existing ids (from dict schema)
    existing_ids = set()
    ov = overlay.get("overrides") if isinstance(overlay, dict) else None
    if isinstance(ov, dict):
        existing_ids.update([_norm(k) for k in ov.keys()])

    # Also gather from legacy list schema if present
    if isinstance(overlay, list):
        for e in overlay:
            try:
                ek = _norm(str(e.get("kind", "")))
                er = _norm(str(e.get("ref", "")))
                existing_ids.add(f"{ek}:{er}")
            except Exception:
                pass

    probe_id = _norm(f"{kind}:{ref}")
    if probe_id in existing_ids:
        msg = {"ok": False, "error": "duplicate_tool", "kind": kind, "ref": ref, "overlay": str(OVERLAY)}
        print(__import__("json").dumps(msg))
        if not allow_update:
            sys.exit(2)
