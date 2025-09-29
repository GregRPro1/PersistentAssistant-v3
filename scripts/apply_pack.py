import subprocess
from pathlib import Path

FILES = {
    'tools/ps1/run_control_server.ps1': "param([string]$BindHost='127.0.0.1',[int]$BindPort=8776)\n$ErrorActionPreference='Stop'\n$u = \"http://$($BindHost):$($BindPort)/control/\"\nWrite-Host \"Starting PA Control standalone at $u\"\npython (Join-Path $PSScriptRoot '..\\py\\control_server.py') --host $BindHost --port $BindPort\n",
    'tools/py/control_server.py': "from flask import Flask, redirect\nimport argparse\ntry:\n    from server.control_console import bp as control_bp, mount_path as control_mount\nexcept Exception as e:\n    raise SystemExit(f\"[control_server] Failed to import server.control_console: {e}\")\napp = Flask(\"pa_control\")\napp.register_blueprint(control_bp, url_prefix=control_mount)\n@app.get('/')\ndef _root(): return redirect(control_mount + '/')\n@app.get('/healthz')\ndef _health(): return 'ok', 200, {'Content-Type':'text/plain'}\ndef main():\n    p = argparse.ArgumentParser()\n    p.add_argument('--host', default='127.0.0.1')\n    p.add_argument('--port', default=8776, type=int)\n    a = p.parse_args()\n    app.run(host=a.host, port=a.port, debug=False)\nif __name__=='__main__': main()\n",
    'tests/smoke/test_control_bp_import.py': "def test_control_bp_import():\n    mod = __import__('server.control_console', fromlist=['bp','mount_path'])\n    assert hasattr(mod, 'bp') and hasattr(mod, 'mount_path')\n",
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
    try: run(['git','checkout','-B','step/PA-331-control-standalone'], root)
    except Exception: pass
    run(['git','add','-A'], root)
    run(['git','commit','-m','PA-331: rename params in run_control_server.ps1 + smoke'], root)
    run(['git','push','-u','origin','step/PA-331-control-standalone'], root)
    print('PA-331 updated. Start with: pwsh tools\\ps1\\run_control_server.ps1')

if __name__=='__main__': main()