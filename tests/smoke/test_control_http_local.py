from flask import Flask
def test_control_http_local():
    m = __import__('server.control_console', fromlist=['bp','mount_path'])
    app = Flask('t'); app.register_blueprint(m.bp, url_prefix=m.mount_path)
    c = app.test_client()
    r = c.get(m.mount_path + '/')
    assert r.status_code == 200
    assert b'Control Console' in r.data
