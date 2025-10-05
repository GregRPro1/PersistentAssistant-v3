# core/project_session.py
# Persistent Assistant v3
# Created: 2025-08-18
# Author: G. Rapson
# Company: GR-Analysis
# Description:
#   Manages selection and persistence of the current project session, and
#   loading/merging of per-project configuration YAML.

from __future__ import annotations
import os
import yaml
from typing import Dict, Any

SESSION_PATH = os.path.join("config", "session.yaml")

DEFAULTS = {
    "project_name": "Persistent Assistant v3",
    "project_root": os.path.abspath("."),
    "plan_path": os.path.join("project", "plans", "project_plan_v3.yaml"),
    # optional: where the project config lives
    "project_config_path": os.path.join("config", "projects", "persistent_assistant_v3.yaml"),
}

def _abspath_under(root: str, p: str) -> str:
    if not p:
        return ""
    return p if os.path.isabs(p) else os.path.abspath(os.path.join(root, p))

def load_session() -> Dict[str, Any] | None:
    """Return session dict if present and minimally valid; else None."""
    if not os.path.exists(SESSION_PATH):
        return None
    try:
        with open(SESSION_PATH, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except Exception:
        return None

    root = data.get("project_root")
    plan = data.get("plan_path")
    if not root or not os.path.isdir(root):
        return None
    if not plan or not os.path.exists(plan):
        # plan relative to root? try to resolve
        candidate = _abspath_under(root, plan or "")
        if not candidate or not os.path.exists(candidate):
            return None
        data["plan_path"] = candidate
    return data

def save_session(session: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(SESSION_PATH), exist_ok=True)
    with open(SESSION_PATH, "w", encoding="utf-8") as f:
        yaml.dump(session, f, allow_unicode=True, sort_keys=False)

def make_default_session() -> Dict[str, Any]:
    sess = dict(DEFAULTS)
    sess["project_root"] = os.path.abspath(sess["project_root"])
    # normalize plan path absolute
    sess["plan_path"] = _abspath_under(sess["project_root"], sess["plan_path"])
    # normalize project_config_path absolute
    cfgp = sess.get("project_config_path")
    if cfgp:
        sess["project_config_path"] = _abspath_under(sess["project_root"], cfgp)
    return sess

def load_project_config(session: Dict[str, Any]) -> Dict[str, Any]:
    """
    Load per-project config and merge resolved absolute paths into a dict:
    returns a dict with keys: project_name, project_root, plan_path, paths{...}
    Creates missing folders listed in paths.
    """
    project_root = session.get("project_root") or os.path.abspath(".")
    cfg_path = session.get("project_config_path")
    merged: Dict[str, Any] = {
        "project_name": session.get("project_name", DEFAULTS["project_name"]),
        "project_root": project_root,
        "plan_path": session.get("plan_path"),
        "paths": {},
    }

    if cfg_path and os.path.exists(cfg_path):
        with open(cfg_path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
        # prefer config values where present
        merged["project_name"] = cfg.get("project_name", merged["project_name"])
        merged["project_root"] = cfg.get("project_root", project_root)
        # plan path: allow relative to root
        plan_p = cfg.get("plan_path") or merged["plan_path"]
        merged["plan_path"] = _abspath_under(merged["project_root"], plan_p)

        # resolve paths
        cfg_paths = cfg.get("paths", {}) or {}
        for k, v in cfg_paths.items():
            merged["paths"][k] = _abspath_under(merged["project_root"], v)

    else:
        # fallback: ensure absolute plan
        merged["plan_path"] = _abspath_under(project_root, merged["plan_path"] or "")

    # ensure folders exist for known path keys
    for k, v in (merged.get("paths") or {}).items():
        if k.endswith("_dir") and v:
            os.makedirs(v, exist_ok=True)

    return merged
