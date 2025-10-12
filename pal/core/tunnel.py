
from __future__ import annotations
import os, re, subprocess, time, logging, shutil
from pathlib import Path
from typing import Optional, Tuple

log = logging.getLogger("pal.tunnel")

def find_cloudflared(install_if_missing: bool = False) -> str:
    # 1) env override
    env_exe = os.getenv("CLOUDFLARED_EXE")
    if env_exe and Path(env_exe).exists():
        return env_exe
    # 2) config hint
    cfg = Path("pal/config/pal_watchdog.json")
    if cfg.exists():
        try:
            import json
            exe = json.loads(cfg.read_text(encoding="utf-8")).get("cloudflared",{}).get("path")
            if exe and Path(exe).exists():
                return exe
        except Exception:
            pass
    # 3) PATH
    path_exe = shutil.which("cloudflared")
    if path_exe:
        return path_exe
    # 4) Common locations
    for p in [r"C:\Program Files (x86)\cloudflared\cloudflared.exe", r"C:\Program Files\cloudflared\cloudflared.exe"]:
        if Path(p).exists():
            return p
    # 5) Optional install attempt
    if install_if_missing:
        for tool, cmd in [
            ("winget", ["winget","install","--id","Cloudflare.cloudflared","-e","--accept-source-agreements","--accept-package-agreements","-h","0"]),
            ("choco",  ["choco","install","cloudflared","-y"]),
        ]:
            if shutil.which(tool):
                try:
                    subprocess.run(cmd, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    path_exe = shutil.which("cloudflared")
                    if path_exe:
                        return path_exe
                except Exception:
                    pass
    raise FileNotFoundError("cloudflared not found. Set CLOUDFLARED_EXE or install via winget/choco.")

def _capture_url_from_output(line: str) -> Optional[str]:
    m = re.search(r"https?://[a-zA-Z0-9\-]+\.trycloudflare\.com", line)
    return m.group(0) if m else None

def quick_tunnel(exe_path: str, port: int = 8787, wait_seconds: float = 45.0) -> Optional[str]:
    logs = Path("tmp/logs"); logs.mkdir(parents=True, exist_ok=True)
    out = (logs / "cloudflared.out.log").open("a", encoding="utf-8")
    err = (logs / "cloudflared.err.log").open("a", encoding="utf-8")
    try:
        p = subprocess.Popen([exe_path, "tunnel", "--url", f"http://localhost:{port}"],
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        url = None; deadline = time.time() + wait_seconds
        while time.time() < deadline and p.poll() is None and not url:
            line = p.stdout.readline() if p.stdout else ""
            if line:
                out.write(line); out.flush()
                u = _capture_url_from_output(line)
                if u: url = u
            else:
                time.sleep(0.2)
        if url:
            Path("reports/ops").mkdir(parents=True, exist_ok=True)
            Path("reports/ops/tunnel_url.txt").write_text(url, encoding="utf-8")
            log.info("captured tunnel url: %s", url)
            return url
        else:
            # capture remaining stderr
            if p.stderr:
                err.write(p.stderr.read() or "")
                err.flush()
            log.warning("no tunnel url captured")
            return None
    finally:
        out.close(); err.close()

def smoke_tunnel() -> tuple[bool, str]:
    rec_dir = Path("reports/smoke"); rec_dir.mkdir(parents=True, exist_ok=True)
    ok = False; steps = []
    try:
        exe = find_cloudflared()
        steps.append(f"cloudflared: {exe}")
        url = quick_tunnel(exe, 8787, 30.0)
        steps.append(f"url: {url}")
        ok = bool(url and url.startswith("http"))
    except Exception as e:
        steps.append(f"error: {e}")
    rec = {"test":"PAL-TUNNEL", "ok": ok, "steps": steps}
    p = rec_dir / "PAL-TUNNEL.json"
    p.write_text(json.dumps(rec, indent=2), encoding="utf-8")
    return ok, str(p)
