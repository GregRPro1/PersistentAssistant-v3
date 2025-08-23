# --- PA_ROOT_IMPORT ---
import sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
# --- /PA_ROOT_IMPORT ---

from __future__ import annotations
import yaml, pathlib

POLICY_PATH = pathlib.Path("config/policies/role_policies.yaml")

def get_role_system_text(role: str) -> str:
    if not POLICY_PATH.exists():
        return ""
    with open(POLICY_PATH, "r", encoding="utf-8") as f:
        d = yaml.safe_load(f) or {}
    roles = d.get("roles", {})
    r = roles.get(role) or roles.get(role.capitalize()) or {}
    return (r.get("system") or "").strip()
