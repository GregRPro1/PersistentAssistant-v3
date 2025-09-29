# server/ops_pages.py
from flask import Blueprint, Response
from pathlib import Path
from string import Template

bp = Blueprint('ops_pages', __name__)
mount_path = '/ops'

_TPL = Template("""<!doctype html>
<html><head><meta charset="utf-8"/><title>PA Ops</title>
<style>body{font-family:system-ui,Segoe UI,Arial,sans-serif;margin:16px} pre{background:#f6f6f6;padding:10px;border-radius:8px;white-space:pre-wrap}</style>
</head><body>
<h1>Ops</h1>
<h3>pack_fetcher.log (tail)</h3><pre>$PF</pre>
<h3>email_watch.log (tail)</h3><pre>$EW</pre>
</body></html>""")

def _tail(p: Path, n=300)->str:
    try:
        lines = p.read_text(encoding='utf-8', errors='ignore').splitlines()
        return '\n'.join(lines[-n:])
    except Exception:
        return '(missing)'

def _root()->Path:
    p = Path(__file__).resolve()
    for _ in range(12):
        if (p/'.git').exists(): return p
        if p.parent==p: break
        p = p.parent
    return Path.cwd()

@bp.get(mount_path + '/')
def ops_home():
    root = _root()
    pf = _tail(root/'reports'/'ops'/'pack_fetcher.log')
    ew = _tail(root/'reports'/'ops'/'email_watch.log')
    return Response(_TPL.substitute(PF=pf, EW=ew), mimetype='text/html')