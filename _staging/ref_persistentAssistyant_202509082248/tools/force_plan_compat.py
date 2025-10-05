import re, hashlib, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
src  = ROOT / "gui" / "main_window.py"
out  = ROOT / "tmp" / "main_window_fixed.py"

def sha256_of(p: pathlib.Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1<<20), b""):
            h.update(ch)
    return h.hexdigest()

if not src.exists():
    print("[ERROR] gui/main_window.py missing")
    raise SystemExit(2)

txt = src.read_text(encoding="utf-8", errors="ignore")
orig_sha = sha256_of(src)

pat = r"from\s+gui\.tabs\.plan_tracker_tab\s+import\s+PlanTrackerTab"
repl = r"from gui.tabs.plan_tracker_tab_compat import PlanTrackerTab"

if re.search(pat, txt):
    txt2 = re.sub(pat, repl, txt, count=1)
    mode = "replaced"
else:
    # Insert an overriding import after the last 'from gui.tabs.' import
    lines = txt.splitlines()
    insert_at = -1
    for i, line in enumerate(lines):
        if re.match(r"\s*from\s+gui\.tabs\.", line):
            insert_at = i
    if insert_at == -1:
        # Fallback: put near the top after any std imports
        insert_at = 0
    lines.insert(insert_at + 1, "from gui.tabs.plan_tracker_tab_compat import PlanTrackerTab  # forced compat")
    txt2 = "\n".join(lines)
    mode = "inserted"

out.write_text(txt2, encoding="utf-8")
print(f"[CANDIDATE] {out}")
print(f"EXPECTED_SHA {orig_sha}")
print(f"MODE {mode}")
