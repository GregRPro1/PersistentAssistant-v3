import json, os, sys, time, subprocess, re
from datetime import datetime, timezone
from urllib.request import urlopen
from urllib.error import URLError

REPO = os.path.abspath(os.getcwd())
CFG_PATH = os.path.join("config", "processes.json")
STATUS_PATH = os.path.join("reports", "ops", "watchdog_status.json")
CRASH_DIR = os.path.join("reports", "ops", "crash_reports")
LOG_DIR = os.path.join("tmp", "logs")
PID_DIR = os.path.join("tmp", "pid")
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(PID_DIR, exist_ok=True)
os.makedirs(os.path.dirname(STATUS_PATH), exist_ok=True)
os.makedirs(CRASH_DIR, exist_ok=True)

def _now():
    return datetime.now(timezone.utc).isoformat()

def _read_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def _write_json(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, path)

class Proc:
    def __init__(self, spec, defaults):
        self.name = spec["name"]
        self.spec = spec
        self.defaults = defaults
        self.proc = None
        self.state = "stopped"
        self.started_at = None
        self.restarts = 0
        self.last_exit = None
        self.last_error = None
        self.stdout_path = spec.get("logs", {}).get("stdout", os.path.join(LOG_DIR, f"{self.name}.out.log"))
        self.stderr_path = spec.get("logs", {}).get("stderr", os.path.join(LOG_DIR, f"{self.name}.err.log"))
        self._log_regex = None
        health = self._health_cfg()
        if "log_regex" in health:
            self._log_regex = re.compile(health["log_regex"])
        self._tail_pos = 0

    def _restart_cfg(self):
        cfg = dict(self.defaults.get("restart", {}))
        cfg.update(self.spec.get("restart", {}))
        return cfg

    def _health_cfg(self):
        base = dict(self.defaults.get("health", {}))
        base.update(self.spec.get("health", {}) or {})
        return base

    def _cmd(self):
        return self.spec["cmd"]

    def _cwd(self):
        return os.path.join(REPO, self.spec.get("cwd", "."))

    def depends(self):
        return self.spec.get("depends_on", [])

    def start(self):
        if self.proc and self.proc.poll() is None:
            return
        os.makedirs(os.path.dirname(self.stdout_path), exist_ok=True)
        os.makedirs(os.path.dirname(self.stderr_path), exist_ok=True)
        stdout_f = open(self.stdout_path, "a", buffering=1, encoding="utf-8", errors="replace")
        stderr_f = open(self.stderr_path, "a", buffering=1, encoding="utf-8", errors="replace")
        try:
            flags = 0
            if hasattr(subprocess, "CREATE_NO_WINDOW"):
                flags |= subprocess.CREATE_NO_WINDOW
            self.proc = subprocess.Popen(
                self._cmd(),
                cwd=self._cwd(),
                stdout=stdout_f,
                stderr=stderr_f,
                creationflags=flags
            )
            self.state = "starting"
            self.started_at = time.time()
            self.last_exit = None
            self.last_error = None
        except Exception as e:
            self.state = "failed"
            self.last_error = f"spawn_error: {e}"
            self._write_crash_summary("spawn_error", str(e))

    def stop(self):
        if not self.proc:
            return
        try:
            self.proc.terminate()
            for _ in range(20):
                if self.proc.poll() is not None:
                    break
                time.sleep(0.1)
            if self.proc.poll() is None:
                self.proc.kill()
        except Exception:
            pass

    def is_running(self):
        return self.proc is not None and self.proc.poll() is None

    def _http_ok(self, url, expect=200, timeout=2):
        try:
            with urlopen(url, timeout=timeout) as r:
                return r.status == expect
        except URLError:
            return False
        except Exception:
            return False

    def _log_regex_match(self):
        if not self._log_regex:
            return None
        path = self.stdout_path
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                f.seek(self._tail_pos)
                chunk = f.read()
                self._tail_pos = f.tell()
        except FileNotFoundError:
            return None
        if not chunk:
            return None
        m = self._log_regex.search(chunk)
        if m:
            return m.group(0)
        return None

    def _write_crash_summary(self, reason, detail):
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        path = os.path.join(CRASH_DIR, f"{self.name}_{ts}.md")
        tail_out = ""
        tail_err = ""
        try:
            if os.path.exists(self.stdout_path):
                with open(self.stdout_path, "rb") as fo:
                    fo.seek(0, os.SEEK_END); end = fo.tell()
                    fo.seek(max(0, end-4000), os.SEEK_SET)
                    tail_out = fo.read().decode("utf-8", "replace")
        except Exception:
            pass
        try:
            if os.path.exists(self.stderr_path):
                with open(self.stderr_path, "rb") as fe:
                    fe.seek(0, os.SEEK_END); end = fe.tell()
                    fe.seek(max(0, end-4000), os.SEEK_SET)
                    tail_err = fe.read().decode("utf-8", "replace")
        except Exception:
            pass
        with open(path, "w", encoding="utf-8") as w:
            w.write(f"# Crash: {self.name}\n\nReason: {reason}\nDetail: {detail}\n\n## stdout tail\n```\n{tail_out}\n```\n## stderr tail\n```\n{tail_err}\n```\n")

    def tick(self, status_bus):
        if self.proc and self.proc.poll() is not None:
            code = self.proc.returncode
            self.last_exit = code
            if code == 0:
                self.state = "stopped"
            else:
                self.state = "failed"
                self._write_crash_summary("nonzero_exit", f"exit={code}")
            self.proc = None
            self.started_at = None

        health = self._health_cfg()
        ok = None
        if "http" in health:
            cfg = health["http"]
            ok = self._http_ok(cfg.get("url"), cfg.get("expect_status", 200), timeout=health.get("timeout", 2))

        if ok is None and self._log_regex:
            m = self._log_regex_match()
            if m:
                ok = True
                pub = (health or {}).get("publish", {})
                pub_file = pub.get("file")
                if pub_file:
                    try:
                        os.makedirs(os.path.dirname(pub_file), exist_ok=True)
                        with open(pub_file, "w", encoding="utf-8") as pf:
                            pf.write(m.strip())
                    except Exception as e:
                        self.last_error = f"publish_error: {e}"

        if self.is_running():
            if ok is True:
                self.state = "healthy"
            elif ok is False:
                grace = health.get("grace", 10)
                if self.started_at and (time.time() - self.started_at) < grace:
                    self.state = "starting"
                else:
                    self.state = "degraded"
            else:
                self.state = "running"
        else:
            self._maybe_restart()

        status_bus[self.name] = self.snapshot()

    def _maybe_restart(self):
        rcfg = self._restart_cfg()
        pol = rcfg.get("policy", "always")
        should = False
        if pol == "always":
            should = True
        elif pol == "on-failure":
            should = (self.last_exit not in (None, 0))
        elif pol == "never":
            should = False
        if not should:
            return
        bo = rcfg.get("backoff", {})
        base = float(bo.get("initial", 1.0))
        factor = float(bo.get("factor", 1.5))
        mmax = float(bo.get("max", 60.0))
        delay = min(mmax, base * (factor ** max(0, self.restarts-1)))
        self.restarts += 1
        time.sleep(delay)
        self.start()

    def snapshot(self):
        return {
            "name": self.name,
            "state": self.state,
            "pid": self.proc.pid if self.proc and self.proc.poll() is None else None,
            "restarts": self.restarts,
            "last_exit": self.last_exit,
            "last_error": self.last_error,
            "stdout": self.stdout_path,
            "stderr": self.stderr_path,
            "started_at": self.started_at,
        }

def load_or_default_config():
    if not os.path.exists(CFG_PATH):
        default = {"version": 1, "processes": []}
        with open(CFG_PATH, "w", encoding="utf-8") as f:
            json.dump(default, f, indent=2)
    with open(CFG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def main():
    cfg = load_or_default_config()
    defaults = cfg.get("defaults", {})
    procspecs = cfg.get("processes", [])
    name_to_spec = {p["name"]: p for p in procspecs}

    # topo order by deps
    order, seen = [], set()
    def visit(n):
        if n in seen: return
        seen.add(n)
        for d in name_to_spec.get(n, {}).get("depends_on", []) or []:
            if d in name_to_spec: visit(d)
        order.append(n)
    for n in name_to_spec: visit(n)
    procs = [Proc(name_to_spec[n], defaults) for n in order]

    for p in procs:
        p.start()
        time.sleep(0.5)

    status = {"ok": True, "started_at": _now(), "processes": {}}
    try:
        while True:
            for p in procs:
                p.tick(status["processes"])
            _write_json(STATUS_PATH, status)
            time.sleep(1.0)
    except KeyboardInterrupt:
        pass
    finally:
        for p in procs:
            p.stop()

if __name__ == "__main__":
    main()
