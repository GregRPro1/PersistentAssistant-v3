#!/usr/bin/env python3
from __future__ import annotations
import json, threading, time, queue, subprocess, os
from http.server import HTTPServer, BaseHTTPRequestHandler

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
STATE_PLAN = os.path.join(REPO, "_state", "plan_status.json")
PLAN_FILE_A = os.path.join(REPO, "pal_project_plan.yaml")
PLAN_FILE_B = os.path.join(REPO, "plans", "roadmap", "consolidated_roadmap.normalized.yaml")

HOST = "127.0.0.1"
PORT = int(os.environ.get("PAL_PHONE_PORT", "5080"))
TOKEN = os.environ.get("PAL_PHONE_TOKEN", "")  # optional bearer token

q = queue.Queue()
log = []  # recent events

def run_cmd(cmd, cwd=None, shell=True, timeout=600):
    try:
        p = subprocess.Popen(cmd, cwd=cwd or REPO, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=shell)
        out, err = p.communicate(timeout=timeout)
        return p.returncode, out.decode("utf-8", errors="replace"), err.decode("utf-8", errors="replace")
    except Exception as e:
        return 1, "", str(e)

def supervisor_post(path: str):
    url = f"http://127.0.0.1:6060{path}"
    code, out, err = run_cmd(f'python scripts/utils/http_post.py "{url}"')
    ok = (code == 0) or out.strip().isdigit()
    return {"ok": ok, "out": out, "err": err, "url": url}

def read_json(p: str):
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

def write_json(p: str, data):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def do_action(item: dict) -> dict:
    kind = (item.get("cmd") or item.get("action") or "").strip()
    res = {"cmd": kind, "ok": False, "out": "", "err": ""}
    if not kind:
        res["err"] = "missing cmd"
        return res

    if kind.startswith("restart:"):
        target = kind.split(":",1)[1]
        if target not in ("heartbeat","planrefresher","bridgeui","phonesvc","all"):
            target = "all"
        r = supervisor_post(f"/control?service={target}&action=restart")
        res.update(r); res["ok"] = r["ok"]; return res

    if kind == "apply-pack":
        zp = item.get("zip_path")
        if not zp or not os.path.exists(zp):
            res["err"] = f"zip_path missing or not found: {zp}"
            return res
        code, out, err = run_cmd(f'python scripts/apply_pack.py -ZipPath "{zp}"')
        res.update(ok=(code==0), out=out, err=err); return res

    if kind.startswith("git:"):
        sub = kind.split(":",1)[1]
        if sub == "status":
            code, out, err = run_cmd("git status")
        elif sub == "addall":
            code, out, err = run_cmd("git add .")
        elif sub == "commit":
            msg = item.get("message") or "phone-commit"
            code, out, err = run_cmd(f'git commit -m "{msg}"')
        elif sub == "push":
            code, out, err = run_cmd("git push")
        else:
            return {"cmd": kind, "ok": False, "err": f"unknown git subcmd: {sub}"}
        return {"cmd": kind, "ok": (code==0), "out": out, "err": err}

    return {"cmd": kind, "ok": False, "err": f"unknown cmd: {kind}"}

def worker():
    while True:
        item = q.get()
        if item is None: break
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        try:
            result = do_action(item)
            log.append({"ts": ts, "req": item, "res": result})
            if len(log) > 100: log.pop(0)
        except Exception as e:
            log.append({"ts": ts, "req": item, "res": {"ok": False, "err": repr(e)}})
        finally:
            q.task_done()

class H(BaseHTTPRequestHandler):
    def _json(self, code=200, obj=None):
        b = json.dumps(obj or {}).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type,Authorization")
        self.end_headers()
        self.wfile.write(b)

    def _auth_ok(self):
        if not TOKEN:
            return True
        hdr = self.headers.get("Authorization","")
        return hdr == f"Bearer {TOKEN}"

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type,Authorization")
        self.end_headers()

    def do_GET(self):
        if not self._auth_ok():
            return self._json(401, {"error":"unauthorized"})
        if self.path == "/" or self.path.startswith("/app"):
            try:
                html_p = os.path.join(REPO, "web", "phone", "index.html")
                with open(html_p, "r", encoding="utf-8") as f:
                    html = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(html.encode("utf-8"))
            except Exception as e:
                self._json(500, {"error": str(e)})
            return
        if self.path.startswith("/health"):
            self._json(200, {"ok": True, "queue": q.qsize(), "log": log[-5:]})
            return
        if self.path.startswith("/queue"):
            self._json(200, {"size": q.qsize(), "recent": log[-10:]})
            return
        if self.path.startswith("/plan/status"):
            state = read_json(STATE_PLAN) or {}
            files = []
            for pth in (PLAN_FILE_B, PLAN_FILE_A):
                if os.path.exists(pth):
                    files.append(os.path.basename(pth))
            self._json(200, {"state": state, "plans": files})
            return
        self._json(404, {"error":"not found"})

    def do_POST(self):
        if not self._auth_ok():
            return self._json(401, {"error":"unauthorized"})
        try:
            length = int(self.headers.get("Content-Length") or 0)
            body = self.rfile.read(length).decode("utf-8") if length>0 else "{}"
            data = json.loads(body or "{}")
        except Exception:
            data = {}
        if self.path.startswith("/queue"):
            q.put(data); self._json(200, {"queued": True, "size": q.qsize()}); return
        if self.path.startswith("/apply-pack"):
            data["cmd"] = "apply-pack"; q.put(data); self._json(200, {"queued": True}); return
        if self.path.startswith("/git"):
            act = data.get("action"); data["cmd"] = f"git:{act}"; q.put(data); self._json(200, {"queued": True}); return
        if self.path.startswith("/plan/select"):
            sel = (data or {}).get("id")
            if not sel: self._json(400, {"error":"missing id"}); return
            st = read_json(STATE_PLAN) or {}
            st["selected_plan"] = sel
            st["timestamp"] = time.time()
            write_json(STATE_PLAN, st)
            self._json(200, {"ok": True, "selected": sel, "state_path": STATE_PLAN}); return
        self._json(404, {"error":"not found"})

def main():
    t = threading.Thread(target=worker, daemon=True); t.start()
    httpd = HTTPServer((HOST, PORT), H)
    print(f"[PHONE] Serving on http://{HOST}:{PORT}  (token={'set' if TOKEN else 'none'})")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()
