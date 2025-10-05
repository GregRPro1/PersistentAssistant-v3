# tools/leb_service.py
# Minimal Local Exec Bridge (LEB) - stdlib only
from __future__ import annotations
import json, os, sys, time, threading, subprocess, traceback
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CFG_PATH = ROOT / "config" / "leb.yaml"
LOG_PATH = ROOT / "logs" / "leb_service.log"

try:
    import yaml  # already in your venv
except Exception as e:
    print("YAML required. Please install pyyaml in the venv.", e, file=sys.stderr)
    sys.exit(2)

def _load_cfg():
    with open(CFG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

def _log(line: str):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(f"[{ts}] {line}\n")

class Handler(BaseHTTPRequestHandler):
    server_version = "LEB/0.1"

    def _json(self, code: int, payload: dict):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type","application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/ping":
            self._json(200, {"ok": True, "service":"LEB", "version":"0.1"})
            return
        if self.path == "/logs":
            try:
                txt = ""
                if LOG_PATH.exists():
                    txt = LOG_PATH.read_text(encoding="utf-8")[-4000:]
                self._json(200, {"ok": True, "logs": txt})
            except Exception as e:
                self._json(500, {"ok": False, "error": str(e)})
            return
        self._json(404, {"ok": False, "error":"not found"})

    def do_POST(self):
        if self.path != "/run":
            self._json(404, {"ok": False, "error":"not found"})
            return
        try:
            length = int(self.headers.get("Content-Length","0"))
            raw = self.rfile.read(length)
            data = json.loads(raw.decode("utf-8")) if raw else {}
            cmd = data.get("cmd","").strip()
            cfg = _load_cfg()
            allow = set(cfg.get("allowlist") or [])
            limit = int((cfg.get("time_limits") or {}).get("run_seconds", 30))
            if cmd not in allow:
                _log(f"DENY cmd={cmd!r}")
                self._json(403, {"ok": False, "error":"command not allowed"})
                return
            _log(f"RUN  cmd={cmd!r}")
            try:
                p = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=limit)
                out = (p.stdout or "")[-4000:]
                err = (p.stderr or "")[-4000:]
                self._json(200, {"ok": True, "rc": p.returncode, "stdout": out, "stderr": err})
                _log(f"DONE rc={p.returncode}")
            except subprocess.TimeoutExpired:
                self._json(408, {"ok": False, "error":"timeout"})
                _log("TIMEOUT")
        except Exception as e:
            _log("EXC " + "".join(traceback.format_exc()[-1200:]))
            self._json(500, {"ok": False, "error": str(e)})

def main():
    cfg = _load_cfg()
    host = cfg.get("bind","127.0.0.1")
    port = int(cfg.get("port", 8765))
    httpd = HTTPServer((host, port), Handler)
    _log(f"LEB start {host}:{port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        _log("LEB stop")

if __name__ == "__main__":
    sys.exit(main())
