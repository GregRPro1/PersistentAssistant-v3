"""
Utilities to print and fetch Master/Sub Context IDs for display.
"""
from __future__ import annotations
import yaml, pathlib

DEFAULT_CFG_REL = "configs/master_context.yaml"

def load_context(cfg_path: str | None = None) -> dict:
    repo_root = pathlib.Path(__file__).resolve().parents[1]
    path = repo_root / (cfg_path or DEFAULT_CFG_REL)
    if not path.exists():
        return {"master_context": "UNSET", "sub_context": "UNSET", "updated_utc": None}
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return {
        "master_context": data.get("master_context", "UNSET"),
        "sub_context": data.get("sub_context", "UNSET"),
        "updated_utc": data.get("updated_utc"),
    }

def banner(prefix: str = "PAL") -> str:
    ctx = load_context()
    lines = [
        "",
        f"{prefix} ─────────────────────────────────────────────────────────────────────",
        f"MasterContext: {ctx.get('master_context')}",
        f"SubContext:    {ctx.get('sub_context')}",
        f"Updated (UTC): {ctx.get('updated_utc')}",
        f"{prefix} ─────────────────────────────────────────────────────────────────────",
        "",
    ]
    return "\n".join(lines)

def print_banner(prefix: str = "PAL") -> None:
    print(banner(prefix))

if __name__ == "__main__":
    print_banner()
