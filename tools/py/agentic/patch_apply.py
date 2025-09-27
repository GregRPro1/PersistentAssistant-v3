# tools/py/agentic/patch_apply.py
from __future__ import annotations
# --- PA_ROOT_IMPORT ---
import sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[3]  # .../tools/py/agentic -> repo root
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
# --- /PA_ROOT_IMPORT ---

import argparse, json, os, fnmatch, shutil, time
from pathlib import Path
from typing import Any, Dict, List, Tuple

from tools.py.agentic.patch_utils import (
    sha256_hex, ensure_dir
)

SCHEMA_PATH = Path(__file__).resolve().parent / "patch_schema.json"
DEFAULT_POLICY = ROOT / "config" / "runner_policy.yaml"

def load_json(path: Path) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def soft_validate_schema(doc: dict) -> tuple[bool, str | None]:
    """Soft schema validation: never block dry-run; in apply mode block on validation failure."""
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

def normalize_repo_path(p: str | Path) -> Path:
    pstr = str(p).replace("\\", "/")
    if os.path.isabs(pstr):
        return Path(pstr)
    return (ROOT / pstr).resolve()

# -------------------- policy loading & checks --------------------

def _safe_yaml_load(raw: str) -> dict:
    try:
        import yaml  # type: ignore
        data = yaml.safe_load(raw) or {}
        if not isinstance(data, dict): return {}
        return data
    except Exception:
        return {}

def load_policy() -> tuple[dict, dict]:
    """
    Returns (effective_policy, diag)
    effective_policy keys:
      enabled, require_feature_id, require_before_sha, allow_globs, deny_globs, backups{enabled,dir}
    diag includes paths tried and used_path.
    """
    paths_tried = []
    env_path = os.environ.get("PA_POLICY_PATH")
    candidates = []
    if env_path:
        candidates.append(Path(env_path))
    candidates.append(DEFAULT_POLICY)

    used_path = None
    raw = ""
    for p in candidates:
        paths_tried.append(str(p))
        if p.exists():
            used_path = p
            raw = p.read_text(encoding="utf-8")
            break

    raw_dict = _safe_yaml_load(raw) if raw else {}

    # new-style section
    ai_apply = raw_dict.get("ai_apply") or {}
    # back-compat flags
    enabled = bool(ai_apply.get("enabled", raw_dict.get("apply_enabled", False)))
    require_feature_id = bool(ai_apply.get("require_feature_id", raw_dict.get("require_feature_id", True)))
    require_before_sha = bool(ai_apply.get("require_before_sha", raw_dict.get("require_before_sha", True)))

    allow_globs = raw_dict.get("allow_globs") or []
    deny_globs = raw_dict.get("deny_globs") or []
    backups = raw_dict.get("backups") or {}
    backups_enabled = bool((backups or {}).get("enabled", True))
    backups_dir = str((backups or {}).get("dir", "tmp/backups"))

    eff = {
        "enabled": enabled,
        "require_feature_id": require_feature_id,
        "require_before_sha": require_before_sha,
        "allow_globs": list(allow_globs),
        "deny_globs": list(deny_globs),
        "backups": {"enabled": backups_enabled, "dir": backups_dir},
    }
    diag = {
        "paths_tried": paths_tried,
        "used_path": str(used_path) if used_path else None,
        "exists": bool(used_path),
        "raw_len": len(raw) if raw else 0,
        "raw_top_keys": list(raw_dict.keys()) if isinstance(raw_dict, dict) else [],
        "effective": eff,
    }
    return eff, diag

def path_is_allowed(rel_posix: str, allow_globs: List[str], deny_globs: List[str]) -> tuple[bool, List[str], List[str]]:
    matched_allow = [pat for pat in allow_globs if fnmatch.fnmatch(rel_posix, pat)]
    matched_deny  = [pat for pat in deny_globs  if fnmatch.fnmatch(rel_posix, pat)]
    if allow_globs and not matched_allow:
        return False, matched_allow, matched_deny
    if matched_deny:
        return False, matched_allow, matched_deny
    return True, matched_allow, matched_deny

# -------------------- main --------------------

def diag_result(path: Path, ok: bool, reason: str, extra: dict | None = None) -> dict:
    rel = str(path.resolve()).replace("\\", "/")
    try:
        rel = str(path.resolve().relative_to(ROOT)).replace("\\", "/")
    except Exception:
        pass
    r = {"path": rel, "ok": ok, "reason": reason}
    if extra: r.update(extra)
    return r

def backup_file(src: Path, backups_dir: Path) -> str | None:
    try:
        ensure_dir(backups_dir)
        ts = time.strftime("%Y%m%d_%H%M%S")
        sha = sha256_hex(src) if src.exists() else "new"
        dst = backups_dir / f"{src.name}.{ts}.{sha}.bak"
        ensure_dir(dst.parent)
        shutil.copy2(src, dst)
        return str(dst)
    except Exception:
        return None

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
        "policy_apply_enabled": False,
        "really_apply": args.really_apply,
        "ts": int(time.time()),
        "results": [],
        "diagnostics": {},
    }

    # Load policy first
    policy, pdiag = load_policy()
    out["policy_apply_enabled"] = bool(policy.get("enabled", False))
    out["diagnostics"]["policy"] = pdiag

    prop_path = normalize_repo_path(args.proposal)
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

    # Soft schema check
    ok_schema, schema_note = soft_validate_schema(proposal)
    if schema_note:
        out["diagnostics"]["schema"] = schema_note
    if not ok_schema and args.really_apply:
        out["diagnostics"]["error"] = "schema_validation_failed_apply_blocked"
        print(json.dumps(out, indent=2))
        return 1

    actions: List[dict] = proposal.get("actions") or proposal.get("changes") or []
    if not isinstance(actions, list) or not actions:
        out["diagnostics"]["error"] = "no_actions_in_proposal"
        print(json.dumps(out, indent=2))
        return 1

    # Preflight policy blocks (apply mode only)
    policy_blocks: List[str] = []
    if args.really_apply:
        if not policy.get("enabled", False):
            policy_blocks.append("policy_disabled")
        if policy.get("require_feature_id", True) and not (out["feature_id"] or "").strip():
            policy_blocks.append("missing_feature_id")

    # Process actions
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

        path = normalize_repo_path(path_raw)
        rel_posix = str(path.resolve().relative_to(ROOT)).replace("\\", "/") if path.exists() or True else str(path_raw)

        # allow/deny check
        allowed, matched_allow, matched_deny = path_is_allowed(
            rel_posix, policy.get("allow_globs", []), policy.get("deny_globs", [])
        )

        exists = path.exists()
        result_extra = {
            "idx": idx,
            "mode": mode,
            "before_sha": before_sha or None,
            "exists": exists,
            "rel": rel_posix,
            "allow_matches": matched_allow,
            "deny_matches": matched_deny,
        }

        if not allowed:
            out["results"].append(diag_result(path, False, "policy_path_not_allowed", result_extra))
            all_ok = False
            continue

        # Current SHA (if file exists)
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

        # require_before_sha policy (apply mode)
        if args.really_apply and policy.get("require_before_sha", True):
            if not before_sha:
                out["results"].append(diag_result(path, False, "missing_before_sha_required", result_extra))
                all_ok = False
                continue

        # before_sha match (when provided)
        if before_sha and have_sha and before_sha != have_sha.lower():
            out["results"].append(diag_result(path, False, "before_sha_mismatch", result_extra))
            all_ok = False
            continue

        # mode preconditions
        if mode == "append" and not exists:
            out["results"].append(diag_result(path, False, "append_target_missing", result_extra))
            all_ok = False
            continue
        if mode == "replace" and not exists:
            out["results"].append(diag_result(path, False, "replace_target_missing", result_extra))
            all_ok = False
            continue
        if mode == "create" and exists:
            out["results"].append(diag_result(path, False, "create_target_already_exists", result_extra))
            all_ok = False
            continue

        # Perform or preview
        if args.really_apply and policy.get("enabled", False) and not policy_blocks:
            # backup if enabled
            if policy.get("backups", {}).get("enabled", True) and exists:
                bdir = normalize_repo_path(policy.get("backups", {}).get("dir", "tmp/backups"))
                result_extra["backup"] = backup_file(path, bdir)

            ensure_dir(path.parent)
            if mode == "append":
                with open(path, "a", encoding="utf-8", newline="") as f:
                    f.write(content)
            elif mode == "replace":
                with open(path, "w", encoding="utf-8", newline="") as f:
                    f.write(content)
            else:  # create
                with open(path, "x", encoding="utf-8", newline="") as f:
                    f.write(content)

            after_sha = sha256_hex(path)
            out["results"].append(diag_result(path, True, "applied",
                                              {**result_extra, "bytes": len(content.encode("utf-8")), "after_sha": after_sha}))
        else:
            out["results"].append(diag_result(path, True, "would_apply",
                                              {**result_extra, "bytes": len(content.encode("utf-8"))}))

    # If we’re in apply mode but blocked at policy level, surface it clearly.
    if args.really_apply and policy_blocks:
        out["diagnostics"]["policy_blocks"] = policy_blocks

    out["ok"] = all_ok and (not args.really_apply or (policy.get("enabled", False) and not policy_blocks))
    print(json.dumps(out, indent=2))
    return 0 if out["ok"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
