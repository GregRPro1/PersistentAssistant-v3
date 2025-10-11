param([string]$BindHost = "127.0.0.1",[int]$Port = 8787)
$python = "$env:VIRTUAL_ENV\Scripts\python.exe"
if (-not (Test-Path $python)) { $python = "python" }
Set-Location -Path $PSScriptRoot
$serverPy = @"
import http.server, socketserver, json, sys
host, port, version = sys.argv[1], int(sys.argv[2]), sys.argv[3]
class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith('/healthz'):
            b = json.dumps({'ok': True, 'version': version}).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type','application/json')
            self.send_header('Content-Length', str(len(b)))
            self.end_headers(); self.wfile.write(b)
        else:
            b = b'PAL placeholder running'
            self.send_response(200)
            self.send_header('Content-Type','text/plain; charset=utf-8')
            self.send_header('Content-Length', str(len(b)))
            self.end_headers(); self.wfile.write(b)
    def log_message(self, *args): pass
with socketserver.TCPServer((host, port), H) as httpd: httpd.serve_forever()
"@
$pyPath = Join-Path $PSScriptRoot "server.py"
Set-Content -Path $pyPath -Value $serverPy -Encoding UTF8
Write-Host "Starting PAL placeholder on http://$BindHost`:$Port ..."
& $python $pyPath $BindHost $Port "0.1.0"
