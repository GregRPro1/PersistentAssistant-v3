# tools/py/lan_control_server.py
from __future__ import annotations
from flask import Flask, Response
import importlib, json, os

# small helper to import blueprints by module name dynamically
def _maybe_register(app: Flask, modname: str, errors: list, mounts: list):
    try:
        m = importlib.import_module(modname)
        bp = getattr(m, 'bp', None)
        mp = getattr(m, 'mount_path', None)
        if bp and mp:
            app.register_blueprint(bp, url_prefix=mp)
            mounts.append({'module': modname, 'prefix': mp})
        else:
            errors.append(f'{modname}: missing bp or mount_path')
    except Exception as e:
        errors.append(f'{modname}: {e.__class__.__name__}: {e}')

def create_app() -> Flask:
    app = Flask('pa_lan')
    errors, mounts = [], []
    # known blueprints (some may be absent)
    for mod in [
        'server.control_console',
        'server.mobile_home',
        'server.ops_pages',
        'server.jobs_api',
        'server.upload_api',  # optional
    ]:
        _maybe_register(app, mod, errors, mounts)

    @app.get('/healthz')
    def healthz():
        return app.response_class(
            response=json.dumps({'ok': True, 'mounts': mounts, 'errors': errors}),
            mimetype='application/json'
        )

    @app.get('/')
    def root():
        return Response('ok', mimetype='text/plain')

    # simple routes inspector
    @app.get('/__debug')
    def dbg():
        lines = []
        for r in app.url_map.iter_rules():
            lines.append(str(r))
        body = 'ROUTES:\n' + '\n'.join(sorted(lines))
        return Response(body, mimetype='text/plain')

    return app

def main():
    host = os.environ.get('PA_LAN_HOST', os.environ.get('HOST', '0.0.0.0'))
    try:
        port = int(os.environ.get('PA_LAN_PORT', os.environ.get('PORT', '8776')))
    except Exception:
        port = 8776
    app = create_app()
    app.run(host=host, port=port)

if __name__ == '__main__':
    main()
