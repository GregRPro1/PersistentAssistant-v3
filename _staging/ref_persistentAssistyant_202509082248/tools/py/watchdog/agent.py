from __future__ import annotations
import subprocess, json, time, urllib.request, urllib.error, pathlib, sys, os
from typing import Tuple, Dict, Any

ROOT = pathlib.Path(__file__).resolve().parents[2]

def http_get(url: str, timeout: float = 2.5) -> Tuple[int, str]:
    try:
        with urllib.request.urlopen(urllib.request.Request(url, method="GET"), timeout=timeout) as r:
            return (r.getcode(), r.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        try:
            body = e.read().decode("utf-8", "replace")
        except Exception:
            body = str(e)
        return (e.code or 0, body)
    except Exception as e:
        return (0, f"{type(e).__name__}: {e}")

def start_and_wait(start_cmd: str, host: str, port: int, health_path: str, timeout_sec: int) -> bool:
    try:
        res = subprocess.run(start_cmd, shell=True, cwd=str(ROOT),
                             capture_output=True, text=True, timeout=timeout_sec)
        # (log sizes only; avoid flooding)
        # print(f"[start] rc={res.returncode} out={len(res.stdout)} err={len(res.stderr)}")
    except subprocess.TimeoutExpired:
        pass
    except Exception:
        pass
    url = f"http://{host}:{port}{health_path}"
    deadline = time.time() + float(timeout_sec)
    while time.time() < deadline:
        code, _ = http_get(url, timeout=1.5)
        if 200 <= code < 300:
            return True
        time.sleep(0.4)
    return False
