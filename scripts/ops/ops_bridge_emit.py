# ops_bridge_emit.py - writes reports/ops/ops_status.json with dev/tracker URLs + timestamp
from __future__ import annotations
import json, time, os
from pathlib import Path

def read_text(path: Path) -> str|None:
    try:
        return path.read_text(encoding='utf-8').strip()
    except Exception:
        return None

def main(repo: Path):
    repo = repo.resolve()
    ops_dir = repo / 'reports' / 'ops'
    ops_dir.mkdir(parents=True, exist_ok=True)
    candidates = [
        repo/'tmp'/'dev_tunnel_url.txt',
        repo/'tmp'/'tracker_tunnel_url.txt',
        repo/'tunnel_url.txt',
        repo/'tmp'/'tunnel_url.txt',
    ]
    urls = {}
    for p in candidates:
        txt = read_text(p)
        if txt and 'trycloudflare.com' in txt:
            name = 'tracker' if 'tracker' in p.name else ('dev' if 'dev' in p.name else 'unknown')
            urls[name] = txt
    payload = {
        'ts': int(time.time()),
        'urls': urls,
        'env': {'PAL_MASTER': os.environ.get('PAL_MASTER'), 'PAL_CHILD': os.environ.get('PAL_CHILD')}
    }
    out = ops_dir / 'ops_status.json'
    out.write_text(json.dumps(payload, indent=2), encoding='utf-8')
    print(f'Wrote {out}')

if __name__ == '__main__':
    repo = Path(os.environ.get('PA_REPO', r'C:\_Repos\PersistentAssistant'))
    main(repo)
