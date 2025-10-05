import sys, pathlib, re, hashlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
src = ROOT / "gui" / "main_window.py"
out = ROOT / "tmp" / "main_window_fixed.py"

def sha256_of(p: pathlib.Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1<<20), b""):
            h.update(ch)
    return h.hexdigest()

if not src.exists():
    print("[SKIP] gui/main_window.py not found")
    raise SystemExit(0)

txt = src.read_text(encoding="utf-8", errors="ignore")
orig_sha = sha256_of(src)

pat_replace = r"from\s+gui\.tabs\.plan_tracker_tab\s+import\s+PlanTrackerTab"
repl        = r"from gui.tabs.plan_tracker_tab_compat import PlanTrackerTab"

if re.search(pat_replace, txt):
    txt2 = re.sub(pat_replace, repl, txt, count=1)
    mode = "replaced"
else:
    # Insert the compat import just after the last 'from gui.tabs.' import line, so it overrides earlier binding
    lines = txt.splitlines()
    insert_at = 0
    for i, line in enumerate(lines):
        if re.match(r"\s*from\s+gui\.tabs\.", line):
            insert_at = i
    lines.insert(insert_at+1, "from gui.tabs.plan_tracker_tab_compat import PlanTrackerTab  # forced compat")
    txt2 = "\n".join(lines)
    mode = "inserted"

out.write_text(txt2, encoding="utf-8")
print(f"[CANDIDATE] tmp/main_window_fixed.py written ({mode})")
print("EXPECTED_SHA", orig_sha)
