#!/usr/bin/env python3
import os, sys, json, time, re, subprocess, datetime, threading, urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(r"C:\_Repos\PersistentAssistant\scripts\config")))
import pal_settings  # type: ignore

REPO = Path(pal_settings.get("paths.repo_root"))
CFG_SERVICES = json.loads((REPO/"config"/"services.json").read_text(encoding="utf-8"))
LOGS = REPO/"logs"; WD_LOG = LOGS/"watchdog"; CF_LOG = LOGS/"cloudflared"; TRK_LOG = LOGS/"tracker"
for d in (WD_LOG, CF_LOG, TRK_LOG): d.mkdir(parents=True, exist_ok=True)

STATE = REPO/"logs"/"watchdog"/"state.json"
URL_PAT = re.compile(r"https://[A-Za-z0-9\-\.]+\.trycloudflare\.com")

LCFG = pal_settings.get("lifecycle")
CHECK_IV = int(LCFG.get("check_interval_sec", 30))
R_LIMIT = int(LCFG.get("restart_limit_count", 3))
R_WINDOW = int(LCFG.get("restart_limit_window_sec", 300))
BACKOFF = int(LCFG.get("backoff_sec", 120))
AUTO_SMOKE = bool(LCFG.get("auto_run_smoke", True))
AUTO_PUSH = bool(LCFG.get("auto_git_push", True))

PIDS = {}         # name -> popen
META = {}         # name -> {pid, last_ok, restarts, backoff_until, logfile}

def _ts(): return datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d_%H%M%S")

def _child_env():
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"; env["PYTHONIOENCODING"] = "utf-8"
    return env

def _log_path(name):
    if name == "cloudflared-tunnel":
        return CF_LOG / f"quick-tunnel_{_ts()}.log"
    return WD_LOG / f"{name}_{_ts()}.log"

def _save_state():
    data = {}
    for n in CFG_SERVICES.keys():
        m = META.get(n, {})
        data[n] = {
            "pid": m.get("pid"),
            "last_ok": m.get("last_ok"),
            "restarts": m.get("restarts", 0),
            "backoff_until": m.get("backoff_until"),
            "logfile": str(m.get("logfile")) if m.get("logfile") else None
        }
    STATE.write_text(json.dumps(data, indent=2), encoding="utf-8")

def _head_ok(url, timeout=2.5):
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status < 400
    except Exception:
        return False

def _tunnel_ok():
    # scan latest cloudflared log for URL
    files = sorted(CF_LOG.glob("quick-tunnel_*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files: return False
    try:
        txt = files[0].read_text(encoding="utf-8", errors="replace")
        return URL_PAT.search(txt) is not None
    except Exception:
        return False

def start(name):
    if name in PIDS and PIDS[name].poll() is None:
        return
    svc = CFG_SERVICES[name]
    logfile = _log_path(name)
    f = open(logfile, "a", buffering=1, encoding="utf-8", errors="replace")
    cmd = svc["cmd"]
    shell = os.name == "nt"
    p = subprocess.Popen(" ".join(cmd) if shell else cmd, cwd=str(REPO), stdout=f, stderr=f, stdin=subprocess.DEVNULL, shell=shell, env=_child_env())
    PIDS[name] = p
    META[name] = {"pid": p.pid, "restarts": META.get(name,{}).get("restarts",0), "logfile": logfile, "last_ok": None, "backoff_until": None}
    _save_state()

def stop(name):
    p = PIDS.get(name)
    if not p: return
    if p.poll() is None:
        try:
            p.terminate()
            for _ in range(25):
                if p.poll() is not None: break
                time.sleep(0.2)
            if p.poll() is None: p.kill()
        except Exception: pass
    PIDS[name] = None
    _save_state()

def healthy(name):
    svc = CFG_SERVICES[name]
    h = svc.get("health")
    if not h:
        ok = PIDS.get(name) and PIDS[name].poll() is None
    elif h.startswith("http"):
        ok = _head_ok(h)
    elif h.startswith("logmatch:"):
        ok = _tunnel_ok()
    else:
        ok = False
    if ok:
        META[name]["last_ok"] = _ts()
        _save_state()
    return ok

def restart(name):
    stop(name); time.sleep(0.3); start(name)
    META[name]["restarts"] = META.get(name,{}).get("restarts",0) + 1; _save_state()

def initialize_all():
    start("pal-dev-server")
    # wait server ok
    for _ in range(60):
        if healthy("pal-dev-server"): break
        time.sleep(1)
    start("pal-tracker")
    for _ in range(30):
        if healthy("pal-tracker"): break
        time.sleep(1)
    start("cloudflared-tunnel")
    for _ in range(30):
        if healthy("cloudflared-tunnel"): break
        time.sleep(1)
    if AUTO_SMOKE:
        run_smoke_and_commit()

def run_smoke_and_commit():
    try:
        py = sys.executable or "python"
        subprocess.run([py, str(REPO/"scripts"/"smoke"/"pal_smoke.py")], cwd=str(REPO), check=False)
    except Exception:
        pass
    if AUTO_PUSH:
        try:
            from scripts.watchdog.git_ops import commit_and_push  # type: ignore
        except Exception:
            import importlib.util, sys as _sys
            spec = importlib.util.spec_from_file_location("git_ops", str(REPO/"scripts"/"watchdog"/"git_ops.py"))
            m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)  # type: ignore
            commit_and_push = m.commit_and_push  # type: ignore
        commit_and_push(REPO, "PAL: Lifecycle start-up verification")

def loop():
    # Continuous heartbeat with restart policy
    hist = {n: [] for n in CFG_SERVICES.keys()}  # timestamps of restarts
    while True:
        for name, svc in CFG_SERVICES.items():
            # respect backoff
            bo = META.get(name, {}).get("backoff_until")
            now = time.time()
            if bo and now < bo:
                continue
            ok = healthy(name)
            p = PIDS.get(name)
            running = bool(p and p.poll() is None)
            if not running or not ok:
                # restart policy
                # purge old entries
                tlist = hist[name] = [t for t in hist[name] if now - t < R_WINDOW]
                if len(tlist) >= R_LIMIT:
                    META[name]["backoff_until"] = now + BACKOFF
                    _save_state()
                    continue
                restart(name)
                hist[name].append(time.time())
                if AUTO_SMOKE:
                    run_smoke_and_commit()
        time.sleep(CHECK_IV)
