# server/control_console.py
import os, subprocess
from pathlib import Path
from string import Template
from flask import Blueprint, request, Response

bp = Blueprint('control_console', __name__)
mount_path = '/control'

REPO_DEFAULT = os.getenv('PA_REPO', 'GregRPro1/PersistentAssistant-v3')
RELEASE_DEFAULT = os.getenv('PA_RELEASE', 'PA-OUTPUT')
ASSET_GLOB_DEFAULT = os.getenv('PA_ASSET_GLOB', 'PA_OUTPUT_*.zip')

def _is_local(req) -> bool:
    ip = (req.remote_addr or '')
    return ip.startswith('127.') or ip == '::1'

def _authz(req) -> bool:
    token = os.getenv('PA_WEB_TOKEN', '').strip()
    if not token:
        return True if _is_local(req) else True  # relaxed for now
    if _is_local(req): return True
    hdr = req.headers.get('Authorization','')
    parts = hdr.split()
    return (len(parts)==2 and parts[0].lower()=='bearer' and parts[1]==token)

def _repo_root() -> Path:
    p = Path(__file__).resolve()
    for _ in range(12):
            if (p/'.git').exists(): return p
            if p.parent==p: break
            p = p.parent
    return Path.cwd()

_TPL = Template("""<!doctype html>
<html><head><meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>PA Control</title>
  <style>
    body{font-family:system-ui,Segoe UI,Arial,sans-serif;margin:24px;max-width:900px}
    label{display:block;margin-top:12px}
    input[type=text]{width:100%;padding:8px}
    .row{display:flex;gap:12px}.row>div{flex:1}
    button{margin-top:16px;padding:8px 14px}
    pre{background:#f6f6f6;padding:10px;overflow:auto}
    .ok{color:green}.err{color:#b00}
  </style>
</head><body>
  <h1>Persistent Assistant — Control Console</h1>
  <form method='POST' action='apply'>
    <div class='row'>
      <div><label>Repo (owner/repo)<input name='repo' value='$REPO'></label></div>
      <div><label>Release tag<input name='release' value='$REL'></label></div>
    </div>
    <label>Asset glob<input name='asset_glob' value='$GLOB'></label>
    <label>Direct ZIP URL (optional)<input name='direct_url' value=''></label>
    <label>GitHub token (optional)<input name='gh_token' value=''></label>
    <button type='submit'>Apply</button>
  </form>
  $EXTRA
  <p>Logs: <code>reports/ops/pack_fetcher.log</code></p>
</body></html>""")

def _page(extra: str='') -> str:
    return _TPL.substitute(REPO=REPO_DEFAULT, REL=RELEASE_DEFAULT, GLOB=ASSET_GLOB_DEFAULT, EXTRA=(extra or ''))

@bp.before_request
def _gate():
    if not _authz(request):
        return Response('Forbidden', status=403)

@bp.get('/')
def ui():
    return Response(_page(), mimetype='text/html')

@bp.post('/apply')
def apply_once():
    if not _authz(request):
        return Response('Forbidden', status=403)

    data = request.form or {}
    repo = (data.get('repo') or REPO_DEFAULT).strip()
    release = (data.get('release') or RELEASE_DEFAULT).strip()
    asset = (data.get('asset_glob') or ASSET_GLOB_DEFAULT).strip()
    direct = (data.get('direct_url') or '').strip()
    token = (data.get('gh_token') or os.getenv('GITHUB_TOKEN','')).strip()

    root = _repo_root()
    py_fetcher = root / 'tools' / 'py' / 'pack' / 'pack_fetcher.py'
    ps1 = root / 'tools' / 'ps1' / 'run_pack_fetcher.ps1'

    env = os.environ.copy()
    if token: env['GITHUB_TOKEN'] = token

    if direct and py_fetcher.exists():
        args = ['python', str(py_fetcher), '--once', '--direct', direct]
    elif py_fetcher.exists():
        args = ['python', str(py_fetcher), '--once', '--repo', repo, '--release', release, '--asset', asset]
    else:
        args = ['pwsh', str(ps1), '-Once']

    try:
        p = subprocess.run(args, cwd=str(root), env=env, capture_output=True, text=True, timeout=600)
        ok = (p.returncode==0)
        klass = 'ok' if ok else 'err'
        extra = "<p class='%s'>Exit %d</p><h3>stdout</h3><pre>%s</pre><h3>stderr</h3><pre>%s</pre>" % (
            klass, p.returncode, (p.stdout or '').replace('<','&lt;'), (p.stderr or '').replace('<','&lt;'))
        return Response(_page(extra), mimetype='text/html', status=(200 if ok else 500))
    except Exception as e:
        return Response(_page("<p class='err'>Exception: %s</p>" % (str(e),)), mimetype='text/html', status=500)
