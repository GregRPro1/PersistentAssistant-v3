def test_tunnel_api_import():
    from server.tunnel_api import tunnel_bp
    from flask import Flask
    app = Flask(__name__)
    app.register_blueprint(tunnel_bp)
    c = app.test_client()
    r = c.get('/api/tunnel')
    assert r.status_code == 200
    data = r.get_json()
    assert 'url' in data and 'running' in data and 'age_s' in data
