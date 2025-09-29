import subprocess
from pathlib import Path

FILES = {
    'tools/py/control_server.py': "# tools/py/control_server.py\nfrom flask import Flask, Response\nimport importlib, traceback\nfrom pathlib import Path\nimport json\n\napp = Flask(\"pa_control\")\n\nMOUNTS = []\nERRORS = []\n\ndef _try_mount(mod_name: str):\n    try:\n        m = importlib.import_module(mod_name)\n        bp = getattr(m, 'bp')\n        prefix = getattr(m, 'mount_path', '/' + mod_name.rsplit('.',1)[-1])\n        app.register_blueprint(bp, url_prefix=prefix)\n        MOUNTS.append({'module': mod_name, 'prefix': prefix})\n        return True\n    except Exception as e:\n        ERRORS.append({'module': mod_name, 'error': str(e), 'trace': traceback.format_exc()})\n        return False\n\n# Mount all known blueprints\nfor name in [\n    'server.control_console',\n    'server.mobile_home',\n    'server.ops_pages',\n    'server.jobs_api',\n]:\n    _try_mount(name)\n\ndef _repo_root() -> Path:\n    p = Path(__file__).resolve()\n    for _ in range(12):\n        if (p/'.git').exists(): return p\n        if p.parent == p: break\n        p = p.parent\n    return Path.cwd()\n\ndef _write_routes_dump():\n    try:\n        lines = [str(r) for r in app.url_map.iter_rules()]\n        body = 'ROUTES:\\n' + '\\n'.join(lines) + '\\n\\nMOUNTS:\\n' + json.dumps(MOUNTS, indent=2) + '\\n\\nERRORS:\\n'\n        body += '\\n'.join([e['module'] + ': ' + e['error'] for e in ERRORS])\n        out = _repo_root()/ 'reports' / 'ops'\n        out.mkdir(parents=True, exist_ok=True)\n        (out / 'control_routes.txt').write_text(body, encoding='utf-8')\n    except Exception:\n        pass\n\n@app.get('/')\ndef root():\n    # simple HTML index of mounts\n    items = ''.join([f'<li><a href=\"{m[\"prefix\"]}/\">{m[\"prefix\"]}/</a> \u2014 {m[\"module\"]}</li>' for m in MOUNTS])\n    html = f'<!doctype html><h1>PA endpoints</h1><ul>{items}</ul>'\n    return Response(html, mimetype='text/html')\n\n@app.get('/healthz')\ndef healthz():\n    payload = {'ok': True, 'mounts': MOUNTS, 'errors': [{'module':e['module'], 'error': e['error']} for e in ERRORS]}\n    return Response(json.dumps(payload), mimetype='application/json')\n\n@app.get('/__debug')\ndef debug():\n    _write_routes_dump()\n    lines = [str(r) for r in app.url_map.iter_rules()]\n    text = 'ROUTES:\\n' + '\\n'.join(lines) + '\\n\\nMOUNTS:\\n' + json.dumps(MOUNTS, indent=2) + '\\n\\n'\n    text += 'ERRORS:\\n' + '\\n'.join([e['module'] + ': ' + e['error'] for e in ERRORS])\n    return Response(text, mimetype='text/plain')\n\nif __name__=='__main__':\n    import argparse\n    p = argparse.ArgumentParser()\n    p.add_argument('--host', default='127.0.0.1')\n    p.add_argument('--port', default=8776, type=int)\n    a = p.parse_args()\n    _write_routes_dump()\n    app.run(host=a.host, port=a.port, debug=False)",
    'tests/smoke/test_control_server_mounts.py': "# tests/smoke/test_control_server_mounts.py\nfrom importlib.machinery import SourceFileLoader\nfrom pathlib import Path\n\ndef _repo_root(start: Path) -> Path:\n    p = start\n    for _ in range(12):\n        if (p/'.git').exists(): return p\n        if p.parent==p: break\n        p = p.parent\n    return start\n\ndef test_standalone_mounts_app_and_ops():\n    root = _repo_root(Path(__file__).resolve())\n    mod_path = root/'tools'/'py'/'control_server.py'\n    mod = SourceFileLoader('control_server_test', str(mod_path)).load_module()\n    app = getattr(mod, 'app')\n    c = app.test_client()\n    assert c.get('/app/').status_code == 200\n    # /ops/ is a simple page; allow 200 even if logs missing\n    assert c.get('/ops/').status_code == 200",
}

def write(root: Path, rel: str, txt: str):
    p = root/rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(txt, encoding='utf-8')

def find_root(seed: Path) -> Path:
    p = seed
    for _ in range(12):
        if (p/'.git').exists(): return p
        if p.parent==p: break
        p = p.parent
    return seed

def run(a, cwd=None, check=False):
    subprocess.run(a, cwd=cwd, check=check)

def main():
    root = find_root(Path(__file__).resolve())
    for rel,txt in FILES.items():
        write(root, rel, txt)
    try: run(['git','checkout','-B','step/PA-341-standalone-mount-all'], root)
    except Exception: pass
    run(['git','add','-A'], root)
    run(['git','commit','-m','PA-341: mount /app, /ops, /api/jobs into standalone control + diagnostics + smoke'], root)
    run(['git','push','-u','origin','step/PA-341-standalone-mount-all'], root)
    print('PA-341 applied.')
    print('Run: pwsh tools\\ps1\\run_control_server.ps1')
    print('Then:  http://127.0.0.1:8776/   (index)')
    print('       http://127.0.0.1:8776/__debug   (routes dump)')
if __name__=='__main__': main()