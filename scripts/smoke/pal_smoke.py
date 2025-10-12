#!/usr/bin/env python3
"""
Non-blocking smoke diagnostics for PAL.
Writes logs/smoke/smoke_<ts>.json and .txt. Prints concise summary.
"""
import os, sys, json, datetime, socket, subprocess, re, urllib.request, pathlib, time, psutil

# Optional dependency: psutil. If not present, we fallback to wmic/tasklist.
try:
    import psutil  # type: ignore
except Exception:
    psutil = None

REPO = pathlib.Path(r"C:\_Repos\PersistentAssistant")
LOGS = REPO / "logs"
SMOKE_DIR = LOGS / "smoke"
TRACKER_DIR = LOGS / "tracker"
WD_LOG_DIR = LOGS / "watchdog"
CF_LOG_DIR = LOGS / "cloudflared"
SMOKE_DIR.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(REPO / "scripts" / "config"))
try:
    import pal_settings  # type: ignore
    CFG = pal_settings.load_settings()
except Exception:
    CFG = {
        "ports": {"watchdog_ui": 9001, "dev_server": 8787, "tracker": 9002},
        "paths": {"repo_root": str(REPO),
                  "tracker_script": str(REPO/'scripts'/'tracker'/'pal_tracker.py')}
    }

def utcnow():
    return datetime.datetime.now(datetime.timezone.utc)

def ts():
    return utcnow().strftime("%Y%m%d_%H%M%S")

def head(url, timeout=2.5):
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, dict(r.headers)
    except Exception as e:
        return None, {"error": str(e)}

def get_python_procs():
    result = []
    if psutil:
        for p in psutil.process_iter(attrs=['pid','name','exe','cmdline','create_time']):
            try:
                if 'python' in (p.info.get('name') or '').lower():
                    exe = p.info.get('exe') or ''
                    cmd = ' '.join(p.info.get('cmdline') or [])
                    if 'PersistentAssistant' in exe or 'PersistentAssistant' in cmd:
                        result.append({"pid": p.info['pid'], "exe": exe, "cmd": cmd, "start": p.info.get('create_time')})
            except Exception:
                pass
    else:
        # fallback rough list via tasklist
        try:
            out = subprocess.check_output(["tasklist", "/V", "/FO", "CSV"], text=True, encoding="utf-8", errors="ignore")
            for line in out.splitlines():
                if "python" in line and "PersistentAssistant" in line:
                    result.append({"raw": line})
        except Exception:
            pass
    return result

def read_latest(path: pathlib.Path, pattern: str):
    files = sorted(path.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
    return files[0] if files else None

def extract_trycloudflare_url(txt: str):
    m = re.search(r"https://[A-Za-z0-9\-\.]+\.trycloudflare\.com", txt)
    return m.group(0) if m else None

def main():
    out = {"ts": ts(), "utc": utcnow().isoformat()}
    ports = CFG.get("ports", {})
    out["config"] = CFG

    # 1) python processes
    out["python_procs"] = get_python_procs()

    # 2) watchdog UI health + dark CSS token
    wd_port = int(ports.get("watchdog_ui", 9001))
    status, hdrs = head(f"http://127.0.0.1:{wd_port}")
    out["watchdog_head"] = {"status": status, "headers": hdrs}
    css_ok = False
    try:
        html = urllib.request.urlopen(f"http://127.0.0.1:{wd_port}", timeout=2.5).read().decode("utf-8", "ignore")
        css_ok = ":root{--bg:#0b0d10;" in html
    except Exception as e:
        html = f"(fetch failed: {e})"
    out["watchdog_css_token"] = css_ok

    # 3) tracker endpoint
    ep_file = TRACKER_DIR / "endpoint.json"
    if ep_file.exists():
        try:
            ep = json.loads(ep_file.read_text(encoding="utf-8"))
        except Exception as e:
            ep = {"error": str(e)}
    else:
        ep = None
    out["tracker_endpoint_json"] = ep

    # 4) tracker script presence and any bound port
    tracker_script = pathlib.Path(CFG["paths"].get("tracker_script", ""))
    out["tracker_script_exists"] = tracker_script.exists()
    # quick scan: check preferred port and next few ports
    tport = int(ports.get("tracker", 9002))
    bound = None
    import socket
    for p in [tport] + list(range(tport, tport+6)):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM); s.settimeout(0.15)
        try:
            s.connect(("127.0.0.1", p)); bound = p; s.close(); break
        except Exception:
            s.close()
    out["tracker_bound_port"] = bound

    # 5) latest logs existence
    latest_wd = read_latest(WD_LOG_DIR, "*_*.log")
    latest_cf = read_latest(CF_LOG_DIR, "*_*.log")
    out["latest_watchdog_log"] = str(latest_wd) if latest_wd else None
    out["latest_cloudflared_log"] = str(latest_cf) if latest_cf else None

    # 6) cloudflared URL extraction
    url = None
    if latest_cf and latest_cf.exists():
        try:
            txt = latest_cf.read_text(encoding="utf-8", errors="replace")
            url = extract_trycloudflare_url(txt)
        except Exception as e:
            url = f"(read err: {e})"
    out["tunnel_url"] = url

    # 7) dev server HEAD
    dev_port = int(ports.get("dev_server", 8787))
    dev_status, _ = head(f"http://127.0.0.1:{dev_port}")
    out["dev_head_status"] = dev_status

    # Write artifacts
    jpath = SMOKE_DIR / f"smoke_{out['ts']}.json"
    tpath = SMOKE_DIR / f"smoke_{out['ts']}.txt"
    jpath.write_text(json.dumps(out, indent=2), encoding="utf-8")
    # concise text
    lines = [
        f"SMOKE {out['ts']}",
        f"python_procs={len(out['python_procs'])}",
        f"watchdog_head={out['watchdog_head']['status']} css={out['watchdog_css_token']}",
        f"tracker_endpoint={'present' if out['tracker_endpoint_json'] else 'absent'} bound_port={out['tracker_bound_port']}",
        f"logs watchdog={'yes' if out['latest_watchdog_log'] else 'no'} cloudflared={'yes' if out['latest_cloudflared_log'] else 'no'}",
        f"tunnel_url={out['tunnel_url']}",
        f"dev_head={out['dev_head_status']}",
        ""
    ]
    tpath.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))

if __name__ == "__main__":
    main()
