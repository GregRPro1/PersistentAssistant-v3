
from __future__ import annotations
import os, re, subprocess, time, logging, shutil, socket, json
from pathlib import Path
from typing import Optional, Tuple, List, Dict

log = logging.getLogger("pal.tunnel")

def is_port_listening(host: str, port: int, timeout: float = 1.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False

def _http_ok(url: str, timeout: float = 3.0) -> bool:
    try:
        import urllib.request
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return 200 <= r.getcode() < 300
    except Exception:
        return False

def find_cloudflared(install_if_missing: bool = False) -> str:
    env_exe = os.getenv("CLOUDFLARED_EXE")
    if env_exe and Path(env_exe).exists():
        return env_exe
    cfg = Path("pal/config/pal_watchdog.json")
    if cfg.exists():
        try:
            exe = json.loads(cfg.read_text(encoding="utf-8")).get("cloudflared",{}).get("path")
            if exe and Path(exe).exists():
                return exe
        except Exception:
            pass
    path_exe = shutil.which("cloudflared")
    if path_exe:
        return path_exe
    for p in [r"C:\Program Files (x86)\cloudflared\cloudflared.exe", r"C:\Program Files\cloudflared\cloudflared.exe"]:
        if Path(p).exists():
            return p
    if install_if_missing:
        for tool, cmd in [
            ("winget", ["winget","install","--id","Cloudflare.cloudflared","-e","--accept-source-agreements","--accept-package-agreements","-h","0"]),
            ("choco",  ["choco","install","cloudflared","-y"]),
        ]:
            if shutil.which(tool):
                try:
                    subprocess.run(cmd, check=False)
                    path_exe = shutil.which("cloudflared")
                    if path_exe:
                        return path_exe
                except Exception as e:
                    log.warning("installer via %s failed: %s", tool, e)
    raise FileNotFoundError(
        "cloudflared not found. Remediation:\n"
        "  1) Install once: winget install --id Cloudflare.cloudflared -e --accept-source-agreements --accept-package-agreements\n"
        "     or: choco install cloudflared -y\n"
        "  2) Or set CLOUDFLARED_EXE to the full path of cloudflared.exe\n"
    )

def _capture_url_from_output(line: str) -> Optional[str]:
    m = re.search(r"https?://[a-zA-Z0-9\-]+\.trycloudflare\.com", line)
    return m.group(0) if m else None

def quick_tunnel(exe_path: str, port: int = 8787, wait_seconds: float = 45.0, verbose: bool = False) -> Tuple[Optional[str], List[str]]:
    print(f"Starting cloudflared quick tunnel to http://localhost:{port}. "
          f"This command RETURNS. Timeout={wait_seconds}s. "
          "If no URL is printed, check tmp/logs/cloudflared.*.log and reports/smoke/PAL-TUNNEL-RUN.json.")
    steps: List[str] = []
    logs = Path("tmp/logs"); logs.mkdir(parents=True, exist_ok=True)
    out_path = logs / "cloudflared.out.log"
    err_path = logs / "cloudflared.err.log"
    steps.append(f"exe={exe_path}")
    steps.append(f"port={port} listening={is_port_listening('127.0.0.1', port)}")
    out = out_path.open("a", encoding="utf-8")
    err = err_path.open("a", encoding="utf-8")
    try:
        cmd = [exe_path, "tunnel", "--url", f"http://localhost:{port}"]
        steps.append("run=" + " ".join(cmd))
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        url = None; deadline = time.time() + wait_seconds
        while time.time() < deadline and (p.poll() is None) and not url:
            line = p.stdout.readline() if p.stdout else ""
            if line:
                out.write(line); out.flush()
                if verbose:
                    print(line.rstrip())
                u = _capture_url_from_output(line)
                if u: url = u; steps.append(f"url={u}")
            else:
                time.sleep(0.2)
        if p.stderr:
            rem = p.stderr.read()
            if rem:
                err.write(rem); err.flush()
        if not url:
            steps.append("no_url_captured")
            log.warning("no tunnel url captured in allotted time")
        else:
            Path("reports/ops").mkdir(parents=True, exist_ok=True)
            Path("reports/ops/tunnel_url.txt").write_text(url, encoding="utf-8")
            steps.append("tunnel_url.txt written")
        return url, steps
    finally:
        out.close(); err.close()

def verify_tunnel_url() -> Tuple[bool, Dict[str,str]]:
    info: Dict[str,str] = {}
    p = Path("reports/ops/tunnel_url.txt")
    if not p.exists():
        return False, {"error":"tunnel_url.txt missing"}
    url = p.read_text("utf-8").strip()
    info["tunnel_url"] = url
    if not url.startswith("http"):
        return False, {"tunnel_url": url, "error":"invalid_url"}
    health = url.rstrip("/") + "/healthz"
    ok = _http_ok(health, 5.0)
    info["tunnel_health"] = health
    info["health_ok"] = str(ok)
    return ok, info

def diagnose_tunnel_path(port: int, health_url: str, install_if_missing: bool, timeout: float, verbose: bool) -> Dict[str, object]:
    report: Dict[str, object] = {"ok": False, "checks": []}
    origin_listening = is_port_listening("127.0.0.1", port)
    report["checks"].append({"origin_port": port, "listening": origin_listening})
    health_ok = _http_ok(health_url, 3.0)
    report["checks"].append({"health_url": health_url, "ok": health_ok})
    if not origin_listening or not health_ok:
        report["error"] = "origin_not_ready"
    try:
        exe = find_cloudflared(install_if_missing=install_if_missing)
        report["cloudflared"] = exe
    except Exception as e:
        report["error"] = f"cloudflared_missing: {e}"
        return report
    url, steps = quick_tunnel(exe_path=exe, port=port, wait_seconds=timeout, verbose=verbose)
    report["steps"] = steps
    if not url:
        report["error"] = "no_url_captured"
        return report
    report["tunnel_url"] = url
    ok = _http_ok(url.rstrip('/') + "/healthz", 5.0)
    report["remote_health_ok"] = ok
    report["ok"] = bool(ok)
    return report
