import sys, pathlib, re, hashlib, time, shutil

ROOT = pathlib.Path(__file__).resolve().parents[1]
src = ROOT / "gui" / "main_window.py"
out = ROOT / "tmp" / "main_window_fixed.py"

def sha256_of(p: pathlib.Path) -> str:
    import hashlib
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1<<20), b""):
            h.update(ch)
    return h.hexdigest()

if not src.exists():
    print("[SKIP] gui/main_window.py not found")
    raise SystemExit(0)

txt = src.read_text(encoding="utf-8", errors="ignore")

pattern = r"from\s+gui\.tabs\.plan_tracker_tab\s+import\s+PlanTrackerTab"
repl    = r"from gui.tabs.plan_tracker_tab_compat import PlanTrackerTab"

if not re.search(pattern, txt):
    print("[SKIP] expected import not found; no replace attempted")
    raise SystemExit(0)

newtxt = re.sub(pattern, repl, txt, count=1)
out.write_text(newtxt, encoding="utf-8")
print("[CANDIDATE] tmp/main_window_fixed.py written")
print("EXPECTED_SHA", sha256_of(src))
