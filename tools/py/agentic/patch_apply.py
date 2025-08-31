# tools/py/agentic/patch_apply.py
from __future__ import annotations
# --- PA_ROOT_IMPORT ---
import sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[3]  # .../tools/py/agentic -> repo root
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
# --- /PA_ROOT_IMPORT ---

import argparse, json, os
from pathlib import Path
from typing import Any, Dict, List

from tools.py.agentic.patch_utils import (
    sha256_hex, ensure_dir  # your existing helpers
)

SCHEMA_PATH = Path(__file__).resolve().parent / "patch_schema.json"

def load_json(path: Path) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def validate_against_schema(doc: dict) -> tuple[bool, str | None]:
    """Soft schema validation: if jsonschema not present or schema missing, do NOT block; just report."""
    try:
        if not SCHEMA_PATH.exists():
            return True, "schema_missing_skipped"
        try:
            import jsonschema  # type: ignore
        except Exception:
            return True, "jsonschema_missing_skipped"
        schema = load_json(SCHEMA_PATH)
        jsonschema.validate(instance=doc, schema=schema)
        return True, None
    except Exception as e:
        return False, f"schema_error: {type(e).__name__}: {e}"

def normalize_path(p: str | Path) -> Path:
    # normalize repo-relative paths
    pstr = str(p).replace("\\", "/")
    if os.path.isabs(pstr):
        return Path(pstr)
    return (ROOT / pstr).resolve()

def diag_result(path: Path, ok: bool, reason: str, extra: dict | None = None) -> dict:
    r = {
        "path": str(path.relative_to(ROOT)) if path.is_absolute() else str(path),
        "ok": ok,
        "reason": reason,
    }
    if extra:
        r.update(extra)
    return r

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--proposal", required=True, help="Path to proposal JSON")
    ap.add_argument("--really-apply", action="store_true", help="Apply instead of dry-run")
    ap.add_argument("--debug", action="store_true", help="Emit extra diagnostics")
    args = ap.parse_args()

    out: Dict[str, Any] = {
        "ok": False,
        "feature_id": None,
        "dry_run": not args.really_apply,
        "policy_apply_enabled": False,  # gate still off for safety
        "really_apply": args.really_apply,
        "ts": int(Path().stat().st_mtime) if hasattr(Path(), "stat") else 0,
        "results": [],
        "diagnostics": {},
    }

    prop_path = normalize_path(args.proposal)
    out["diagnostics"]["proposal_path"] = str(prop_path)

    if not prop_path.exists():
        out["diagnostics"]["error"] = "proposal_not_found"
        print(json.dumps(out, indent=2))
        return 1

    try:
        proposal = load_json(prop_path)
    except Exception as e:
        out["diagnostics"]["error"] = f"proposal_json_error: {type(e).__name__}: {e}"
        print(json.dumps(out, indent=2))
        return 1

    out["feature_id"] = proposal.get("feature_id")

    # Soft schema check (never hard-block dry-run on schema)
    ok_schema, schema_note = validate_against_schema(proposal)
    if schema_note:
        out["diagnostics"]["schema"] = schema_note
    if not ok_schema and args.really_apply:
        out["diagnostics"]["error"] = "schema_validation_failed_apply_blocked"
        print(json.dumps(out, indent=2))
        return 1

    actions: List[dict] = proposal.get("actions") or []
    if not isinstance(actions, list) or not actions:
        out["diagnostics"]["error"] = "no_actions_in_proposal"
        print(json.dumps(out, indent=2))
        return 1

    all_ok = True
    for idx, action in enumerate(actions, start=1):
        path_raw = action.get("path")
        mode = (action.get("mode") or "append").lower()
        content = action.get("content", "")
        before_sha = (action.get("before_sha") or "").lower().strip()

        if not path_raw or mode not in {"append", "replace", "create"}:
            out["results"].append(diag_result(Path(path_raw or ""), False, "invalid_action_fields",
                                              {"idx": idx, "mode": mode, "have_path": bool(path_raw)}))
            all_ok = False
            continue

        path = normalize_path(path_raw)
        exists = path.exists()
        result_extra = {
            "idx": idx,
            "mode": mode,
            "before_sha": before_sha or None,
            "exists": exists,
        }

        # Compute current sha if exists
        have_sha = None
        if exists:
            try:
                have_sha = sha256_hex(path)
            except Exception as e:
                out["results"].append(diag_result(path, False, "sha_read_error",
                                                  {**result_extra, "error": f"{type(e).__name__}: {e}"}))
                all_ok = False
                continue
            result_extra["have_sha"] = have_sha

        # before_sha gating: if provided, require exact match when file exists
        if before_sha and have_sha and before_sha != have_sha.lower():
            out["results"].append(diag_result(path, False, "before_sha_mismatch",
                                              {**result_extra}))
            all_ok = False
            continue

        # mode-specific preconditions
        if mode == "append":
            if not exists:
                out["results"].append(diag_result(path, False, "append_target_missing", result_extra))
                all_ok = False
                continue
        elif mode == "replace":
            if not exists:
                out["results"].append(diag_result(path, False, "replace_target_missing", result_extra))
                all_ok = False
                continue
        elif mode == "create":
            if exists:
                out["results"].append(diag_result(path, False, "create_target_already_exists", result_extra))
                all_ok = False
                continue

        # If we got here, we *could* perform the action
        if args.really_apply and out["policy_apply_enabled"]:
            ensure_dir(path.parent)
            if mode == "append":
                with open(path, "a", encoding="utf-8", newline="") as f:
                    f.write(content)
            elif mode == "replace":
                ensure_dir(path.parent)
                with open(path, "w", encoding="utf-8", newline="") as f:
                    f.write(content)
            else:  # create
                ensure_dir(path.parent)
                with open(path, "x", encoding="utf-8", newline="") as f:
                    f.write(content)
            # compute after sha
            after_sha = sha256_hex(path)
            out["results"].append(diag_result(path, True, "applied",
                                              {**result_extra, "bytes": len(content.encode("utf-8")), "after_sha": after_sha}))
        else:
            # dry-run path
            out["results"].append(diag_result(path, True, "would_apply",
                                              {**result_extra, "bytes": len(content.encode("utf-8"))}))

    out["ok"] = all_ok and (not args.really_apply or out["policy_apply_enabled"])
    print(json.dumps(out, indent=2))
    return 0 if out["ok"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
