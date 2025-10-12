
from __future__ import annotations
import json, socket, time, logging, psutil
from pathlib import Path
from typing import Dict, Any, Optional
import yaml

log = logging.getLogger("pal.ops")

OPS_PATH = Path('reports/ops/ops_status.json')
CFG_DEFAULT = {
    "web": {"host": "127.0.0.1", "port": 8787, "health": "http://127.0.0.1:8787/healthz"},
    "tunnel": {"url_file": "reports/ops/tunnel_url.txt", "enabled": True},
}

def ensure_dirs():
    OPS_PATH.parent.mkdir(parents=True, exist_ok=True)
    Path('reports/smoke').mkdir(parents=True, exist_ok=True)
    Path('tmp/logs').mkdir(parents=True, exist_ok=True)

def read_yaml(path: Path) -> Dict[str, Any]:
    if path.is_file():
        try:
            return yaml.safe_load(path.read_text('utf-8')) or {}
        except Exception:
            return {}
    return {}

def read_ops() -> Optional[Dict[str, Any]]:
    if OPS_PATH.is_file():
        try:
            return json.loads(OPS_PATH.read_text('utf-8'))
        except Exception:
            return None
    return None

def _lan_ip() -> Optional[str]:
    try:
        # naive best-effort: pick first non-loopback in private ranges
        for iface, addrs in psutil.net_if_addrs().items():
            for a in addrs:
                if a.family.name == 'AF_INET':
                    ip = a.address
                    if ip.startswith('127.') or ip.startswith('169.254.'):
                        continue
                    if ip.startswith('10.') or ip.startswith('192.168.') or ip.startswith('172.'):
                        return ip
    except Exception:
        return None
    return None

def _is_good_url(u: str) -> bool:
    return isinstance(u, str) and u.startswith(('http://','https://')) and '.' in u

def write_ops_snapshot(config_path: Path) -> Dict[str, Any]:
    ensure_dirs()
    cfg = CFG_DEFAULT.copy()
    cfg_yaml = read_yaml(config_path)
    cfg.update(cfg_yaml or {})
    web = cfg.get('web', {})
    host = web.get('host', '127.0.0.1'); port = int(web.get('port', 8787)); health = web.get('health')
    # TCP check
    port_ok = False
    import socket
    try:
        with socket.create_connection((host, port), timeout=1.2):
            port_ok = True
    except Exception:
        port_ok = False
    # HTTP health (best-effort)
    health_ok = False
    if health:
        try:
            import urllib.request
            with urllib.request.urlopen(health, timeout=2.0) as r:
                health_ok = (200 <= r.getcode() < 300)
        except Exception:
            health_ok = False
    # Tunnel URL
    tun_cfg = cfg.get('tunnel', {}); tun_url = ""
    url_file = Path(tun_cfg.get('url_file', 'reports/ops/tunnel_url.txt'))
    if url_file.is_file():
        raw = url_file.read_text('utf-8').strip()
        if _is_good_url(raw):
            tun_url = raw
    lan = _lan_ip()
    phone_lan = f"http://{lan}:{port}" if lan else ""
    phone_url = tun_url or phone_lan
    st = {
        "ts": time.strftime('%Y-%m-%dT%H:%M:%S'),
        "web": {"host": host, "port": port, "port_ok": port_ok, "health_url": health, "health_ok": health_ok},
        "tunnel": {"url": tun_url, "ok": bool(tun_url)},
        "watcher": {"on": True},  # Python loop marks itself on
        "phone": {"lan": phone_lan, "url": phone_url},
    }
    OPS_PATH.write_text(json.dumps(st, ensure_ascii=False, indent=2), encoding='utf-8')
    log.info("ops snapshot written")
    return st
