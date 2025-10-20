#!/usr/bin/env python3
from __future__ import annotations
import re, sys, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PATTERNS = [
    (r"pal_project_plan\.yaml", "hardcoded path to old plan"),
    (r"active_plan", "expects old 'active_plan' key"),
    (r"\bplans\b", "expects 'plans' dict schema"),
    (r"selected_plan", "uses _state/plan_status.json selected_plan"),
    (r"consolidated_roadmap\.yaml", "new roadmap file"),
    (r"items\",?\s*:", "expects 'items' list schema"),
]

def scan_py(root: Path):
    findings = []
    for p in root.rglob("*.py"):
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        hits = []
        for pat, note in PATTERNS:
            if re.search(pat, text):
                hits.append({"pattern": pat, "note": note})
        if hits:
            findings.append({"file": str(p.relative_to(root)), "hits": hits})
    return findings

def main() -> int:
    out = scan_py(ROOT)
    print(json.dumps({"findings": out}, indent=2))
    has_old = any(any(h["note"].startswith("hardcoded") or h["note"].startswith("expects old") for h in f["hits"]) for f in out)
    sys.exit(1 if has_old else 0)

if __name__ == "__main__":
    raise SystemExit(main())
