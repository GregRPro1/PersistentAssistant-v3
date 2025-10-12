#!/usr/bin/env python3
import json, os, sys, time, subprocess, socket, signal, threading, datetime, pathlib

REPO_ROOT = r"C:\_Repos\PersistentAssistant"
CONFIG = os.path.join(REPO_ROOT, "watchdog", "watchdog.json")
LOG_DIR = os.path.join(REPO_ROOT, "logs", "watchdog")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_PATH = os.path.join(LOG_DIR, f"watchdog_{datetime.datetime.utcnow().strftime('%Y%m%d')}.log")

def log(msg):
    ts = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%SZ")
    line = f"{ts} {msg}"
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line + "\n")
    print(line)

def load_config():
    if not os.path.exists(CONFIG):
        raise FileNotFoundError(f"Config not found: {CONFIG}")
    with open(CONFIG, "r", encoding="utf-8") as f:
        return json.load(f)

def listeners():
    # Windows netstat parsing via subprocess (avoid psutil dependency)
    try:
        out = subprocess.check_output(["netstat", "-ano"], text=True, stderr=subprocess.STDOUT)
    except Exception as e:
        return []
    result = []
    for line in out.splitlines():
        if "LISTENING" in line:
            parts = [p for p in line.split() if p]
            if len(parts) >= 5:
                local = parts[1]
                pid = parts[-1]
                if ":" in local:
                    try:
                        port = int(local.rsplit(":", 1)[-1])
                        result.append((port, int(pid), local))
                    except:  # noqa
                        pass
    return result

def stop_by_port(ports):
    ls = listeners()
    for p in ports:
        for port, pid, _ in ls:
            if port == p:
                try:
                    os.kill(pid, signal.SIGTERM)
                except Exception:
                    try:
                        subprocess.run(["taskkill", "/PID", str(pid), "/F"], check=False, capture_output=True)
                    except Exception:
                        pass

def http_head(url, timeout=2.0):
    # Minimal HEAD using curl if present; fallback to socket
    curl = shutil.which("curl") or shutil.which("curl.exe")
    if curl:
        try:
            cp = subprocess.run([curl, "-I", "-s", url], capture_output=True, text=True, timeout=timeout)
            return cp.returncode == 0 and "HTTP/" in (cp.stdout or "")
        except Exception:
            return False
    # socket fallback (very naive)
    try:
        import urllib.parse
        u = urllib.parse.urlparse(url)
        host = u.hostname or "127.0.0.1"
        port = u.port or (443 if u.scheme == "https" else 80)
        with socket.create_connection((host, port), timeout=timeout) as s:
            s.sendall(f"HEAD {u.path or '/'} HTTP/1.0\r\nHost: {host}\r\n\r\n".encode())
            data = s.recv(64)
        return b"HTTP/" in data
    except Exception:
        return False

def svc_ports(svc):
    return [int(p) for p in (svc.get("ports") or [])]

def start_proc(cwd, cmd):
    log(f"Starting: {cmd} (cwd {cwd})")
    # launch hidden via powershell? keep it simple: new console-less python
    subprocess.Popen(cmd, cwd=cwd, shell=True)

def action_killports(cfg):
    ports = sorted(set(sum([svc_ports(s) for s in cfg["services"]], [])))
    if ports:
        log(f"Killports: {ports}")
        stop_by_port(ports)
    print("=== PACK/STATUS: killports done ===")

def action_start(cfg):
    for s in cfg["services"]:
        if ports := svc_ports(s):
            stop_by_port(ports)
        start_proc(s["start"]["cwd"], s["start"]["command"])
    print("=== PACK/STATUS: start requested ===")

def action_stop(cfg):
    # Only port-based stop (safe, no wildcards)
    for s in cfg["services"]:
        if ports := svc_ports(s):
            stop_by_port(ports)
    print("=== PACK/STATUS: stop requested ===")

def action_restart(cfg):
    action_stop(cfg)
    time.sleep(1)
    action_start(cfg)
    print("=== PACK/STATUS: restart requested ===")

def action_status(cfg):
    for s in cfg["services"]:
        ok = True
        url = (s.get("health") or {}).get("url", "")
        if url:
            ok = http_head(url)
        print(f"{s['name']:<16} ports=[{','.join(map(str, svc_ports(s)))}] health={ok}")

def action_run(cfg):
    poll = int(cfg["watchdog"].get("poll_seconds", 3))
    log("Watchdog started (python)")
    while True:
        for s in cfg["services"]:
            url = (s.get("health") or {}).get("url", "")
            if url and not http_head(url):
                log(f"{s['name']}: health failed; (re)starting")
                if ports := svc_ports(s):
                    stop_by_port(ports)
                start_proc(s["start"]["cwd"], s["start"]["command"])
        time.sleep(poll)

def main():
    if len(sys.argv) < 2:
        print("Usage: watchdog.py [killports|start|stop|restart|status|run]")
        sys.exit(2)
    cfg = load_config()
    action = sys.argv[1]
    if   action == "killports": action_killports(cfg)
    elif action == "start":     action_start(cfg)
    elif action == "stop":      action_stop(cfg)
    elif action == "restart":   action_restart(cfg)
    elif action == "status":    action_status(cfg)
    elif action == "run":       action_run(cfg)
    else:
        print("Unknown action"); sys.exit(2)

if __name__ == "__main__":
    import shutil
    main()
