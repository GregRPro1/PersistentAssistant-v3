# tools/py/control_server.py
from flask import Flask, Response
import importlib, traceback
from pathlib import Path
import json

app = Flask("pa_control")

MOUNTS = []
ERRORS = []

def _try_mount(mod_name: str):
    try:
        m = importlib.import_module(mod_name)
        bp = getattr(m, 'bp')
        prefix = getattr(m, 'mount_path', '/' + mod_name.rsplit('.',1)[-1])
        app.register_blueprint(bp, url_prefix=prefix)
        MOUNTS.append({'module': mod_name, 'prefix': prefix})
        return True
    except Exception as e:
        ERRORS.append({'module': mod_name, 'error': str(e), 'trace': traceback.format_exc()})
        return False

# Mount all known blueprints
for name in [
    'server.control_console',
    'server.mobile_home',
    'server.ops_pages',
    'server.jobs_api',
]:
    _try_mount(name)

def _repo_root() -> Path:
    p = Path(__file__).resolve()
    for _ in range(12):
        if (p/'.git').exists(): return p
        if p.parent == p: break
        p = p.parent
    return Path.cwd()

def _write_routes_dump():
    try:
        lines = [str(r) for r in app.url_map.iter_rules()]
        body = 'ROUTES:\n' + '\n'.join(lines) + '\n\nMOUNTS:\n' + json.dumps(MOUNTS, indent=2) + '\n\nERRORS:\n'
        body += '\n'.join([e['module'] + ': ' + e['error'] for e in ERRORS])
        out = _repo_root()/ 'reports' / 'ops'
        out.mkdir(parents=True, exist_ok=True)
        (out / 'control_routes.txt').write_text(body, encoding='utf-8')
    except Exception:
        pass

@app.get('/')
def root():
    # simple HTML index of mounts
    items = ''.join([f'<li><a href="{m["prefix"]}/">{m["prefix"]}/</a> — {m["module"]}</li>' for m in MOUNTS])
    html = f'<!doctype html><h1>PA endpoints</h1><ul>{items}</ul>'
    return Response(html, mimetype='text/html')

@app.get('/healthz')
def healthz():
    payload = {'ok': True, 'mounts': MOUNTS, 'errors': [{'module':e['module'], 'error': e['error']} for e in ERRORS]}
    return Response(json.dumps(payload), mimetype='application/json')

@app.get('/__debug')
def debug():
    _write_routes_dump()
    lines = [str(r) for r in app.url_map.iter_rules()]
    text = 'ROUTES:\n' + '\n'.join(lines) + '\n\nMOUNTS:\n' + json.dumps(MOUNTS, indent=2) + '\n\n'
    text += 'ERRORS:\n' + '\n'.join([e['module'] + ': ' + e['error'] for e in ERRORS])
    return Response(text, mimetype='text/plain')

if __name__=='__main__':
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('--host', default='127.0.0.1')
    p.add_argument('--port', default=8776, type=int)
    a = p.parse_args()
    _write_routes_dump()
    app.run(host=a.host, port=a.port, debug=False)