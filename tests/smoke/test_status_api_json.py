# tests/smoke/test_status_api_json.py
import importlib
from flask import Flask

def test_status_overview_keys():
    m = importlib.import_module('server.status_api')
    app = Flask('t'); app.register_blueprint(m.bp, url_prefix=m.mount_path)
    c = app.test_client()
    r = c.get('/api/status/overview')
    assert r.status_code == 200
    j = r.get_json()
    assert 'checks' in j and isinstance(j['checks'], dict)
    for k in ['server','mobile','control','upload_api','jobs_api','pack_fetcher','email_watcher']:
        assert k in j['checks']
