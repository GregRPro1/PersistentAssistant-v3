from __future__ import annotations
import re, sys, pathlib, yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
RULES = ROOT / "tools" / "forbidden_patterns.yaml"

def load_rules():
    with open(RULES, "r", encoding="utf-8") as f:
        d = yaml.safe_load(f) or {}
    forb = [re.compile(p, re.IGNORECASE|re.MULTILINE) for p in (d.get("forbidden") or [])]
    exds = d.get("exclude_dirs") or []
    return forb, exds

def is_excluded(p: pathlib.Path, exds: list[str]) -> bool:
    rel = p.relative_to(ROOT).as_posix()
    for pat in exds:
        if re.search(pat, rel, re.IGNORECASE):
            return True
    return False

def scan():
    forb, exds = load_rules()
    hits = []
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

def main():
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
