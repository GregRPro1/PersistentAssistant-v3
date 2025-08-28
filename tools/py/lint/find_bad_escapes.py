# tools/py/lint/find_bad_escapes.py
# Report (and optionally fix) unknown escape sequences inside *non-raw* Python string literals.
# Usage:
#   python tools/py/lint/find_bad_escapes.py --report
#   python tools/py/lint/find_bad_escapes.py --apply   # writes .bak.YYYYmmdd_HHMMSS
from __future__ import annotations
import os, sys, re, time, tokenize
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

ALLOWED = set(list("\\'\"abfnrtvxuUN") + [str(d) for d in range(0,8)])  # digits = octal

def is_raw_prefix(prefix: str) -> bool:
    p = prefix.lower()
    return "r" in p  # treat any combo with r (r, fr, rf, rb, br, ur, ru) as raw

def iter_py_files(root: Path):
    for p in root.rglob("*.py"):
        if any(x in p.parts for x in (".venv","venv",".git","__pycache__")):
            continue
        yield p

def find_issues(path: Path):
    issues = []
    try:
        with open(path, "rb") as fh:
            for tok in tokenize.tokenize(fh.readline):
                if tok.type != tokenize.STRING:
                    continue
                raw = tok.string  # includes prefix and quotes
                m = re.match(r"(?i)^([rubf]+)?([\'\"]).*", raw)
                if m and is_raw_prefix(m.group(1) or ""):
                    continue  # raw strings: skip
                # find backslash + next char that isn't allowed
                for m2 in re.finditer(r"\\(.)", raw):
                    c = m2.group(1)
                    if c not in ALLOWED:
                        issues.append((tok.start[0], m2.group(0)))
    except Exception:
        pass
    return issues

def apply_fix(path: Path):
    bak = f"{path}.bak.{time.strftime('%Y%m%d_%H%M%S')}"
    txt = path.read_text(encoding="utf-8", errors="replace")
    # double only the backslashes that start an unknown escape
    def repl(m):
        ch = m.group(1)
        if ch in ALLOWED:  # keep known escapes intact
            return "\\" + ch
        return "\\\\" + ch   # add an extra backslash
    new_txt = re.sub(r"\\(.)", lambda m: repl(m), txt)
    if new_txt != txt:
        Path(bak).write_text(txt, encoding="utf-8")
        path.write_text(new_txt, encoding="utf-8")
        return True, bak
    return False, None

def main():
    apply = ("--apply" in sys.argv)
    total = 0; files = 0
    for p in iter_py_files(ROOT):
        issues = find_issues(p)
        if issues:
            files += 1
            for line, esc in issues:
                print(f"{p}:{line}: unknown escape {esc}")
            total += len(issues)
            if apply:
                changed, bak = apply_fix(p)
                if changed:
                    print(f"[FIXED] {p} (backup: {bak})")
    print(f"SUMMARY: files_with_issues={files} issues={total}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
