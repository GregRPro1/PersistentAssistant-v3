# tests/smoke/test_blueprint_paths.py
import importlib
from flask import Flask

def _app_with(bp_mod):
    m = importlib.import_module(bp_mod)
    app = Flask('t'); app.register_blueprint(m.bp, url_prefix=m.mount_path)
    return app, m

def test_mobile_at_app_root():
    app, m = _app_with('server.mobile_home')
    r = app.test_client().get('/app/')
    assert r.status_code == 200

def test_ops_at_ops_root():
    app, m = _app_with('server.ops_pages')
    r = app.test_client().get('/ops/')
    assert r.status_code == 200

def test_control_at_control_root():
    app, m = _app_with('server.control_console')
    r = app.test_client().get('/control/')
    assert r.status_code == 200

def test_jobs_paths_ok():
    app, m = _app_with('server.jobs_api')
    c = app.test_client()
    res = c.post('/api/jobs/apply', json={'direct_url':'https://example.com/fake.zip'})
    assert res.status_code == 200
    jid = res.get_json()['id']
    c.get(f'/api/jobs/{jid}')
    c.get(f'/api/jobs/{jid}/tail?n=5')
