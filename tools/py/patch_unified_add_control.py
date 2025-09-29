import sys, yaml
from pathlib import Path
def main():
    root = Path(__file__).resolve()
    for _ in range(8):
        if (root/'.git').exists(): break
        if root.parent==root: break
        root = root.parent
    cfg = root/'config'/'unified_server.yaml'
    if not cfg.exists():
        sys.exit(0)
    data = yaml.safe_load(cfg.read_text(encoding='utf-8')) or {}
    cands = list(data.get('candidates', []))
    if 'server.control_console' not in cands:
        cands.append('server.control_console')
        data['candidates'] = cands
        cfg.write_text(yaml.safe_dump(data, sort_keys=False), encoding='utf-8')
if __name__=='__main__': main()