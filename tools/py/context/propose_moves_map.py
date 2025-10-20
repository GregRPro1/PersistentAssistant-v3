#!/usr/bin/env python3
import re
from pathlib import Path

ROOT = Path(".").resolve()
OUT  = Path("moves_map.yml")

EXCLUDE_DIRS = {
    ".venv","_archive","_context","__pycache__",".git",
    "node_modules","dist","build","out",".idea",".vscode",
    ".pytest_cache",".mypy_cache"
}

def should_exclude(rel: str) -> bool:
    return any(part in EXCLUDE_DIRS for part in rel.split("/"))

# Add rules here as needed. Order matters; first match wins.
RULES = [
    # Agentic kit → agents/kit
    (r"^tools/py/agentic/(.*)$",                 r"agents/kit/\1"),
    # Tool registry → core/registry
    (r"^tools/py/registry/(.*)$",                r"core/registry/\1"),
    (r"^tools/tools/(tool_catalog\..*)$",        r"core/registry/\1"),
    # Legacy LEB stack → legacy/leb
    (r"^tools/py/leb/(.*)$",                     r"legacy/leb/\1"),
    (r"^tools/leb_(.*)$",                        r"legacy/leb/leb_\1"),
    # Optional: normalize cloudflared scripts under scripts/tunnel/
    (r"^scripts/cloudflared/(.*)$",              r"scripts/tunnel/\1"),
]

moves = []
for p in ROOT.rglob("*"):
    if not p.is_file():
        continue
    rel = p.relative_to(ROOT).as_posix()
    if should_exclude(rel):
        continue
    for pat, repl in RULES:
        if re.match(pat, rel):
            to = re.sub(pat, repl, rel)
            if to != rel:
                moves.append({"from": rel, "to": to})
            break

if moves:
    OUT.write_text(
        "moves:\n" + "\n".join(f"  - from: {m['from']}\n    to:   {m['to']}" for m in moves),
        encoding="utf-8"
    )
    print(f"[OK] proposed {len(moves)} moves -> {OUT}")
else:
    print("[OK] no moves proposed (rules matched none)")
