from __future__ import annotations
import os, json
from pathlib import Path
from typing import Any, Dict, List, Tuple

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None  # we still report this in diagnostics

SCRIPT_DIR = Path(__file__).resolve().parent
# /repo/tools/py/agentic  -> repo root is parents[3]
ROOT = SCRIPT_DIR.parents[3]

def _norm(p: Path | str) -> str:
    return str(p).replace("\\", "/")

def _try_paths(custom: str | None) -> List[Path]:
    paths: List[Path] = []
    if custom:
        paths.append(Path(custom))
    env = os.environ.get("PA_POLICY_PATH")
    if env:
        paths.append(Path(env))
    paths.append(ROOT / "config" / "runner_policy.yaml")
    paths.append(Path.cwd() / "config" / "runner_policy.yaml")
    return paths

def load_policy(custom_path: str | None = None) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Returns (effective, diagnostics)
    - effective: normalized, minimal policy the executors care about
    - diagnostics: exhaustive info (paths tried, used, parse errors, raw keys, etc.)
    """
    tried = [_norm(p) for p in _try_paths(custom_path)]
    used: str | None = None
    exists = False
    raw_text: str | None = None
    parse_error: str | None = None
    parsed: Dict[str, Any] | None = None

    for p in _try_paths(custom_path):
        if p.exists():
            used = _norm(p)
            exists = True
            try:
                raw_text = p.read_text(encoding="utf-8", errors="replace")
                if not yaml:
                    parse_error = "pyyaml_not_installed"
                    parsed = {}
                else:
                    parsed = yaml.safe_load(raw_text) or {}
            except Exception as e:  # pragma: no cover
                parse_error = f"{type(e).__name__}: {e}"
                parsed = {}
            break

    # Normalize to an "effective" structure regardless of old/new shapes
    cfg = parsed or {}
    ai_apply = (cfg.get("ai_apply") or {}) if isinstance(cfg, dict) else {}

    enabled = bool(ai_apply.get("enabled")) or bool(cfg.get("apply_enabled"))
    require_feature_id = bool(ai_apply.get("require_feature_id") or cfg.get("require_feature_id"))
    require_before_sha = bool(ai_apply.get("require_before_sha") or cfg.get("require_before_sha"))

    allow_globs = list(cfg.get("allow_globs") or [])
    deny_globs  = list(cfg.get("deny_globs") or [])

    backups = cfg.get("backups") or {}
    backups_enabled = bool(backups.get("enabled"))
    backups_dir = backups.get("dir") or "tmp/backups"

    effective = {
        "enabled": enabled,
        "require_feature_id": require_feature_id,
        "require_before_sha": require_before_sha,
        "allow_globs": allow_globs,
        "deny_globs": deny_globs,
        "backups": {"enabled": backups_enabled, "dir": backups_dir},
    }

    diagnostics = {
        "cwd": _norm(Path.cwd()),
        "script_dir": _norm(SCRIPT_DIR),
        "guessed_root": _norm(ROOT),
        "paths_tried": tried,
        "used_path": used,
        "exists": exists,
        "raw_len": (len(raw_text) if isinstance(raw_text, str) else None),
        "parse_error": parse_error,
        "raw_top_keys": (sorted(list(parsed.keys())) if isinstance(parsed, dict) else []),
        "effective": effective,
    }
    return effective, diagnostics

def match_globs(path: str, allow: List[str], deny: List[str]) -> Dict[str, Any]:
    """Report exactly which patterns match (proves allow/deny behavior)."""
    import fnmatch
    posix = path.replace("\\", "/")
    m_allow = [g for g in allow if fnmatch.fnmatch(posix, g)]
    m_deny  = [g for g in deny  if fnmatch.fnmatch(posix, g)]
    return {"path": posix, "matched_allow": m_allow, "matched_deny": m_deny}
