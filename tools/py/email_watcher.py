import sys
from pathlib import Path
try:
    import yaml
except Exception:
    yaml=None
def load_cfg(p: Path):
    if p.exists():
        if yaml: return yaml.safe_load(p.read_text(encoding='utf-8'))
        data={}
        for line in p.read_text(encoding='utf-8').splitlines():
            if ':' in line:
                k,v=line.split(':',1); data[k.strip()]=v.strip()
        return data
    return {'enabled': False}
def main():
    cfg=load_cfg(Path('config/email_watch.yaml'))
    if not cfg.get('enabled'): 
        print('email watcher disabled; exiting 0'); return 0
    Path(cfg.get('save_dir','_inbox')).mkdir(parents=True, exist_ok=True)
    return 0
if __name__=='__main__': sys.exit(main())
