# tests/smoke/test_lan_server_boot.py
from tools.py.lan_control_server import create_app

def test_healthz_ok():
    app = create_app()
    c = app.test_client()
    r = c.get('/healthz')
    assert r.status_code == 200
    j = r.get_json()
    assert j.get('ok') is True
    # at least one blueprint should be present (mobile or control)
    assert any(m['prefix'] in ['/app','/control'] for m in j.get('mounts',[]))
