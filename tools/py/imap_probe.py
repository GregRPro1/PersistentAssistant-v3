import imaplib, ssl, sys
from pathlib import Path
try:
    import yaml
except Exception:
    yaml=None
def load_cfg(p: Path):
    if not p.exists(): raise SystemExit(f"config not found: {p}")
    txt = p.read_text(encoding='utf-8')
    if yaml:
        return yaml.safe_load(txt)
    cfg={}
    for line in txt.splitlines():
        if ':' in line and not line.strip().startswith('#'):
            k,v=line.split(':',1); cfg[k.strip()]=v.strip()
    return cfg
def main():
    import argparse
    ap=argparse.ArgumentParser()
    ap.add_argument('--config', default='config/email_watch.yaml')
    a=ap.parse_args()
    cfg = load_cfg(Path(a.config))
    host = cfg.get('host'); port=int(cfg.get('port',993)); user=cfg.get('username'); pwd=cfg.get('password')
    print(f"Connecting to {host}:{port} as {user}")
    ctx=ssl.create_default_context()
    with imaplib.IMAP4_SSL(host, port, ssl_context=ctx) as M:
        print("Server greeting:", M.welcome.decode('utf-8','ignore'))
        try:
            code, data = M.login(user, pwd)
            print("LOGIN:", code, data)
        except imaplib.IMAP4.error as e:
            print("LOGIN FAILED:", e); sys.exit(2)
        code, caps = M.capability()
        print("CAPABILITY:", code, caps)
        M.logout()
    print("OK"); return 0
if __name__=='__main__': sys.exit(main())
