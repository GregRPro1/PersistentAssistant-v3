from flask import Flask, redirect
import argparse
try:
    from server.control_console import bp as control_bp, mount_path as control_mount
except Exception as e:
    raise SystemExit(f"[control_server] Failed to import server.control_console: {e}")
app = Flask("pa_control")
app.register_blueprint(control_bp, url_prefix=control_mount)
@app.get('/')
def _root(): return redirect(control_mount + '/')
@app.get('/healthz')
def _health(): return 'ok', 200, {'Content-Type':'text/plain'}
def main():
    p = argparse.ArgumentParser()
    p.add_argument('--host', default='127.0.0.1')
    p.add_argument('--port', default=8776, type=int)
    a = p.parse_args()
    app.run(host=a.host, port=a.port, debug=False)
if __name__=='__main__': main()
