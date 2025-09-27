from __future__ import annotations
import os, pathlib
from typing import Dict, Any, Tuple

try:
    import yaml  # type: ignore
except Exception:
    yaml = None  # tests don't require YAML writeability beyond simple load

ROOT = pathlib.Path(__file__).resolve().parents[1]
CFG  = ROOT / "config" / "ai" / "providers.yaml"

_DEFAULTS = {
    "provider": os.getenv("AI_PROVIDER", "openai"),
    "model":    os.getenv("AI_MODEL", "gpt-4o-mini"),
}

def _read_yaml(path: pathlib.Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8")
    if yaml is None:
        # Minimal YAML: handle empty or a trivial subset
        # For our tests we expect well-formed yaml with simple maps.
        import json as _json
        try:
            return _json.loads(text)  # accept json-as-yaml
        except Exception:
            return {}
    data = yaml.safe_load(text) or {}
    if not isinstance(data, dict):
        return {}
    return data

def load_map() -> Dict[str, Any]:
    data = _read_yaml(CFG)
    default = data.get("default") or {}
    roles   = data.get("roles")   or {}
    if not isinstance(default, dict): default = {}
    if not isinstance(roles, dict):   roles   = {}
    merged_default = {**_DEFAULTS, **default}
    return {"default": merged_default, "roles": roles}

def select_model(role: str) -> Tuple[str, str]:
    m = load_map()
    role_cfg = m["roles"].get(role) or {}
    if not isinstance(role_cfg, dict):
        role_cfg = {}
    provider = str(role_cfg.get("provider", m["default"]["provider"]))
    model    = str(role_cfg.get("model",    m["default"]["model"]))
    return provider, model

def get_client(role: str, **kwargs):
    # Construct a real AIClient using the selected provider/model.
    # Tests don't exercise API calls—this just wires it up.
    from core.ai_client import AIClient
    provider, model = select_model(role)
    return AIClient(provider=provider, model=model, **kwargs)
