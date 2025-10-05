import re, hashlib, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
src  = ROOT / "gui" / "main_window.py"
out  = ROOT / "tmp" / "main_window_with_tree.py"

def sha256_of(p: pathlib.Path) -> str:
    import hashlib
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
changed = False

# Ensure import
if "from gui.tabs.plan_tree_tab import PlanTreeTab" not in txt:
    # insert after last gui.tabs import
    lines = txt.splitlines()
    insert_at = -1
    for i, line in enumerate(lines):
        if re.match(r"\s*from\s+gui\.tabs\.", line):
            insert_at = i
    if insert_at == -1: insert_at = 0
    lines.insert(insert_at+1, "from gui.tabs.plan_tree_tab import PlanTreeTab  # added Plan (Tree) tab")
    txt = "\n".join(lines)
    changed = True

# Ensure addTab call (avoid duplicate)
if "Plan (Tree)" not in txt:
    # naive heuristic: append after first addTab line or after setup of tabs
    add_idx = -1
    lines = txt.splitlines()
    for i, line in enumerate(lines):
        if ".addTab(" in line:
            add_idx = i
            break
    inject = '        self.tabs.addTab(PlanTreeTab(), "Plan (Tree)")  # auto-added\n'
    if add_idx != -1:
        # insert just after the first addTab occurrence
        lines.insert(add_idx+1, inject.rstrip())
    else:
        # find self.tabs creation
        made = False
        for i, line in enumerate(lines):
            if "QTabWidget(" in line and "self.tabs" in line:
                lines.insert(i+1, inject.rstrip())
                made = True
                break
        if not made:
            # fallback: append near end of __init__
            for i, line in enumerate(lines):
                if "def __init__(" in line:
                    # find next 'self.setCentralWidget' or end of function
                    pass
            lines.append(inject.rstrip())
    txt = "\n".join(lines)
    changed = True

out.write_text(txt, encoding="utf-8")
print(f"[CANDIDATE] {out}")
print(f"EXPECTED_SHA {orig_sha}")
print(f"CHANGED {changed}")
