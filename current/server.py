
# current/server.py
# Minimal placeholder HTTP server with sane defaults and /healthz.
import http.server, socketserver, json, sys, os

DEFAULT_HOST = os.environ.get("PAL_DEV_HOST", "127.0.0.1")
DEFAULT_PORT = int(os.environ.get("PAL_DEV_PORT", "8787"))
DEFAULT_VER  = os.environ.get("PAL_DEV_VERSION", "pal-0.1.0")

def parse_args(argv):
    # Accept optional: host port version
    host = DEFAULT_HOST
    port = DEFAULT_PORT
    ver  = DEFAULT_VER
    if len(argv) >= 2:
        host = argv[1]
    if len(argv) >= 3:
        try:
            port = int(argv[2])
        except ValueError:
            pass
    if len(argv) >= 4:
        ver = argv[3]
    return host, port, ver

class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/healthz":
            payload = {"status":"ok","version": self.server.version}
            data = json.dumps(payload).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type","application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        else:
            body = f"<html><body><h1>PAL Dev Server</h1><p>Version: {self.server.version}</p></body></html>".encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type","text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

def main(argv):
    host, port, version = parse_args(argv)
    with socketserver.TCPServer((host, port), Handler) as httpd:
        httpd.version = version
        print(f"PAL Dev Server listening on http://{host}:{port} (version {version})")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass

if __name__ == "__main__":
    main(sys.argv)
