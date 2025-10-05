# tools\preflight_no_heredoc.py
import sys, re, json, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
FORB = [r"<<\s*'?:?PY'", r"python\s*-\s*<<", r"python\s+-c\s+"]
hits=[]
for pattern in FORB:
    rx = re.compile(pattern, re.IGNORECASE)
    for p in ROOT.rglob("*"):
        if p.is_file() and p.suffix.lower() in ('.py','.ps1','.yaml','.yml','.txt','.md','.json','.ini','.cfg','.bat'):
            try:
                t = p.read_text(encoding='utf-8', errors='ignore')
            except Exception:
                continue
            m = rx.search(t)
            if m:
                hits.append({"file": str(p), "pattern": pattern, "sample": m.group(0)})
print(json.dumps({"ok": len(hits)==0, "hits": hits}, indent=2))
sys.exit(0)  # WARN-ONLY: never block
