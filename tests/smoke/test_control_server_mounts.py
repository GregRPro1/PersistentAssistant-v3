# tests/smoke/test_control_server_mounts.py
from importlib.machinery import SourceFileLoader
from pathlib import Path

def _repo_root(start: Path) -> Path:
    p = start
    for _ in range(12):
        if (p/'.git').exists(): return p
        if p.parent==p: break
        p = p.parent
    return start

def test_standalone_mounts_app_and_ops():
    root = _repo_root(Path(__file__).resolve())
    mod_path = root/'tools'/'py'/'control_server.py'
    mod = SourceFileLoader('control_server_test', str(mod_path)).load_module()
    app = getattr(mod, 'app')
    c = app.test_client()
    assert c.get('/app/').status_code == 200
    # /ops/ is a simple page; allow 200 even if logs missing
    assert c.get('/ops/').status_code == 200