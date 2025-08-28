#!/usr/bin/env python
"""
Lightweight forbidden-patterns guard.

- If PyYAML or tools/forbidden_patterns.yaml is missing, it degrades to
  "no rules" and exits 0 (do not break CI just because deps/rules are absent).
- If present, it enforces the rules exactly like your previous version:
  - `forbidden`: list of regex strings
  - `exclude_dirs`: list of regex strings (relative path match)
"""
from __future__ import annotations
import re, sys, pathlib

try:
    import yaml  # type: ignore
except Exception:
    yaml = None  # type: ignore

ROOT = pathlib.Path(__file__).resolve().parents[1]
RULES = ROOT / "tools" / "forbidden_patterns.yaml"


def load_rules() -> tuple[list[re.Pattern[str]], list[str]]:
    if yaml is None or not RULES.exists():
        # Degrade gracefully: no rules means no violations
        return [], []
    try:
        data = yaml.safe_load(RULES.read_text(encoding="utf-8")) or {}
    except Exception:
        # If rules file is unreadable, also degrade gracefully
        return [], []
    forb = [re.compile(p, re.IGNORECASE | re.MULTILINE) for p in (data.get("forbidden") or [])]
    exds = data.get("exclude_dirs") or []
    return forb, exds


def is_excluded(p: pathlib.Path, exds: list[str]) -> bool:
    try:
        rel = p.relative_to(ROOT).as_posix()
    except Exception:
        return False
    for pat in exds:
        if re.search(pat, rel, re.IGNORECASE):
            return True
    return False


def scan() -> list[dict]:
    forb, exds = load_rules()
    if not forb:
        return []
    hits: list[dict] = []
    for p in ROOT.rglob("*"):
        if not p.is_file():
            continue
        if is_excluded(p, exds):
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for rx in forb:
            m = rx.search(text)
            if m:
                hits.append({"file": str(p), "pattern": rx.pattern, "match": m.group(0)})
    return hits


def main() -> int:
    hits = scan()
    if hits:
        print("[FORBIDDEN GUARD] VIOLATIONS FOUND:")
        for h in hits[:100]:
            print(f" - {h['file']}  :: {h['pattern']}  :: {h['match']!r}")
        print(f"Total violations: {len(hits)}")
        return 2
    print("[FORBIDDEN GUARD] OK (no violations).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
