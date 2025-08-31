# tools/py/agentic/patch_apply.py

# allow running as a script or as a module
if __package__ in (None, ""):
    import os, sys
    _here = os.path.dirname(__file__)
    _pkg_root = os.path.dirname(_here)              # tools/py
    if _pkg_root not in sys.path:
        sys.path.insert(0, _pkg_root)
    __package__ = "agentic"


import os, sys, json, time, argparse, glob
from typing import Any, Dict, List
try:
    import yaml  # type: ignore
except Exception:
    yaml = None  # type: ignore

from .patch_utils import (
    ensure_dir, sha256_hex, path_allowed,
    make_backup, apply_append, apply_replace, apply_unified_diff
)

ROOT = os.path.abspath(os.getcwd())
POLICY_PATH = os.path.join(ROOT, "config", "runner_policy.yaml")
OUT_DIR = os.path.join(ROOT, "tmp", "patches")

def load_policy(path: str) -> Dict[str, Any]:
    if yaml and os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    # default policy if file missing
    return {
        "ai_apply": {"enabled": False, "require_feature_id": True},
        "limits": {"max_files": 10, "max_total_bytes": 200000, "max_hunks_per_file": 20},
        "allow_globs": ["**"],
        "deny_globs": ["tmp/**", ".git/**"],
        "backups": {"enabled": True, "dir": "tmp/backups"},
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--proposal", required=True, help="proposal JSON file")
    ap.add_argument("--really-apply", action="store_true", help="override policy ai_apply.enabled")
    args = ap.parse_args()

    policy = load_policy(POLICY_PATH)
    allow, deny = policy.get("allow_globs", []), policy.get("deny_globs", [])
    backups_cfg = policy.get("backups", {"enabled": True, "dir": "tmp/backups"})
    ai_apply_enabled = bool(policy.get("ai_apply", {}).get("enabled"))
    require_feature = bool(policy.get("ai_apply", {}).get("require_feature_id", True))
    effective_apply = args.really_apply or ai_apply_enabled

    with open(args.proposal, "r", encoding="utf-8") as f:
        prop = json.load(f)

    feature_id = (prop.get("feature_id") or "").strip()
    if require_feature and not feature_id:
        print(json.dumps({"ok": False, "err": "missing feature_id"}, indent=2))
        return 2

    dry_run = bool(prop.get("dry_run", True))
    changes: List[Dict[str, Any]] = prop.get("changes") or []
    ts = int(time.time())
    ensure_dir(OUT_DIR)

    results = []
    total_bytes = 0
    for ch in changes:
        rel = ch.get("path")
        mode = ch.get("mode")
        content = ch.get("content", "")
        diff_text = ch.get("patch", "")
        expected = (ch.get("expected_sha256") or "").lower()

        if not rel or not mode:
            results.append({"path": rel, "ok": False, "err": "missing path/mode"})
            continue

        path = os.path.join(ROOT, rel)
        if not os.path.isfile(path):
            results.append({"path": rel, "ok": False, "err": "file not found"})
            continue

        if not path_allowed(rel, allow, deny):
            results.append({"path": rel, "ok": False, "err": "path denied by policy"})
            continue

        try:
            cur_sha = sha256_hex(path)
        except Exception as e:
            results.append({"path": rel, "ok": False, "err": f"sha256: {e}"})
            continue

        if expected and expected != cur_sha:
            results.append({"path": rel, "ok": False, "err": f"sha mismatch (expected {expected}, got {cur_sha})"})
            continue

        before_bytes = os.path.getsize(path)
        if mode in ("append", "replace"):
            total_bytes += len(content.encode("utf-8"))
        elif mode == "patch":
            total_bytes += len(diff_text.encode("utf-8"))

        if not effective_apply or dry_run:
            results.append({"path": rel, "ok": True, "dry_run": True, "mode": mode, "before_sha": cur_sha, "bytes": before_bytes})
            continue

        # apply
        try:
            if backups_cfg.get("enabled", True):
                backup_dir = os.path.join(ROOT, backups_cfg.get("dir", "tmp/backups"))
                make_backup(path, backup_dir)
            if mode == "append":
                apply_append(path, content)
            elif mode == "replace":
                apply_replace(path, content)
            elif mode == "patch":
                apply_unified_diff(path, diff_text)
            else:
                raise ValueError(f"unknown mode {mode}")
            after_sha = sha256_hex(path)
            results.append({"path": rel, "ok": True, "dry_run": False, "mode": mode, "before_sha": cur_sha, "after_sha": after_sha})
        except Exception as e:
            results.append({"path": rel, "ok": False, "err": str(e)})

    out = {
        "ok": all(r.get("ok") for r in results) if results else False,
        "feature_id": feature_id,
        "dry_run": (not effective_apply) or dry_run,
        "policy_apply_enabled": ai_apply_enabled,
        "really_apply": args.really_apply,
        "ts": ts,
        "results": results,
    }
    rep_path = os.path.join(OUT_DIR, f"report_{ts}.json")
    with open(rep_path, "w", encoding="utf-8") as w:
        json.dump(out, w, indent=2)
    print(json.dumps(out, indent=2))
    return 0 if out["ok"] else 1

if __name__ == "__main__":
    sys.exit(main())
