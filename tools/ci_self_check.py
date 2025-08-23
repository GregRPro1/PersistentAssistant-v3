import os, re, sys, pathlib, json

ROOT = pathlib.Path(__file__).resolve().parents[1]
def ok(p): return p.exists()

problems = []

# Basic presence
must_exist = [
  "main.py", "core/ai_client.py", "gui/main_window.py",
  "config/projects/persistent_assistant_v3.yaml",
  "tools/apply_and_pack.py", "tools/run_with_capture.py"
]
for rel in must_exist:
  if not ok(ROOT/rel):
    problems.append(f"[MISSING] {rel}")

# Forbidden patterns (no bash heredocs; no inline python -c in our repo – 3rd party allowed)
for rel in ROOT.rglob("*.{py,yaml,ps1}".replace("{","").replace("}","").split(",")):
  try:
    p = pathlib.Path(rel)
    txt = p.read_text(encoding="utf-8", errors="ignore")
    if "python - <<" in txt or re.search(r'<<\\s*\\'?PY\\'?', txt):
      # allow under venv/site-packages:
      if ".venv" not in str(p):
        problems.append(f"[FORBIDDEN] {p} contains heredoc-like pattern")
  except Exception as e:
    problems.append(f"[READFAIL] {rel}: {e}")

# Import sanity
sys.path.insert(0, str(ROOT))
try:
  import core.ai_client  # noqa
except Exception as e:
  problems.append(f"[IMPORT] core.ai_client: {e}")

print(json.dumps({"ok": not problems, "problems": problems}, indent=2))
raise SystemExit(0 if not problems else 1)
