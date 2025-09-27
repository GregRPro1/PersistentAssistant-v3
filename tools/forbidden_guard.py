from __future__ import annotations
import os, re, sys, json, pathlib, time

ROOT = pathlib.Path(__file__).resolve().parents[1]

# --- What to scan (keep tight) ---
TEXT_EXTS = {
    ".py",".ps1",".psm1",".cmd",".bat",
    ".md",".txt",".rst",
    ".yml",".yaml",".json",".toml",".ini",
    ".sh",".cfg",".conf",".env",
}

# --- Hard excludes (dirs/files) ---
EXCLUDE_DIRS = {
    ".git", ".venv", "tmp", "logs", "node_modules", "__pycache__"
}
EXCLUDE_GLOBS = {
    "**/__pycache__/**", "**/*.pyc", "**/*.pyo",
}
EXCLUDE_FILES_REGEX = [
    re.compile(r"(?i)OpenAI_Interaction\.md$"),
    re.compile(r"(?i)project/structure/"),
    re.compile(r"(?i)config/guidance/"),
]

# Always skip scanning the guard itself
SELF_BASENAME = pathlib.Path(__file__).name

# Allow extra runtime skips via env (semicolon-separated regexes)
def _extra_skips():
    raw = os.environ.get("FORBIDDEN_EXTRA_SKIPS","").strip()
    if not raw:
        return []
    rx = []
    for part in raw.split(";"):
        part = part.strip()
        if not part:
            continue
        try:
            rx.append(re.compile(part))
        except re.error:
            pass
    return rx

EXTRA_SKIP_RX = _extra_skips()

# --- Forbidden patterns ---
PATTERNS = [
    (re.compile(r"<<\s*':?PY'"),           "<< 'PY'"),
    (re.compile(r"python\s*-\s*<<"),       "python - <<"),
    (re.compile(r"python\s+-c\s+"),        "python -c "),
]

def _is_texty(path: pathlib.Path) -> bool:
    if path.suffix.lower() in TEXT_EXTS:
        return True
    # Permit scanning extensionless scripts
    return path.suffix == ""

def _should_skip(path: pathlib.Path) -> bool:
    p = str(path).replace("\\","/")
    # Skip self
    if path.name == SELF_BASENAME and path.parent == pathlib.Path(__file__).parent:
        return True
    # Skip directories in path
    parts = set(part.lower() for part in path.parts)
    if parts & {d.lower() for d in EXCLUDE_DIRS}:
        return True
    # Skip glob-like excludes (cheap check)
    for rx in EXCLUDE_FILES_REGEX:
        if rx.search(p):
            return True
    for rx in EXTRA_SKIP_RX:
        if rx.search(p):
            return True
    return False

def scan():
    violations = []
    scanned = 0
    skipped  = 0
    for path in ROOT.rglob("*"):
        if path.is_dir():
            continue
        if _should_skip(path):
            skipped += 1
            continue
        if not _is_texty(path):
            skipped += 1
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            skipped += 1
            continue
        scanned += 1
        for rx, name in PATTERNS:
            if rx.search(text):
                violations.append({"path": str(path), "pattern": name})
    return {"violations": violations, "scanned": scanned, "skipped": skipped}

def main() -> int:
    t0 = time.time()
    res = scan()
    dt = time.time() - t0
    v = res["violations"]
    if not v:
        print(f"[FORBIDDEN GUARD] OK  (scanned={res['scanned']} skipped={res['skipped']} in {dt:.2f}s)")
        return 0
    print("[FORBIDDEN GUARD] VIOLATIONS FOUND:\n")
    for item in v:
        print(f" - {item['path']}  :: {item['pattern']!r}")
    print(f"\nTotal violations: {len(v)} (scanned={res['scanned']} skipped={res['skipped']} in {dt:.2f}s)")
    # Optional machine-readable drop (under tmp/, which we skip next time)
    try:
        out = ROOT / "tmp" / "logs" / f"guard_report_{int(time.time())}.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(res, indent=2), encoding="utf-8")
    except Exception:
        pass
    return 2

if __name__ == "__main__":
    raise SystemExit(main())
