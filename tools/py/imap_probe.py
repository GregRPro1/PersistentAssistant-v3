import imaplib, ssl, sys
from pathlib import Path
try:
    import yaml
except Exception:
    yaml=None
def load_cfg(p: Path):
    if not p.exists(): raise SystemExit(f"config not found: {p}")
    txt = p.read_text(encoding='utf-8')
    if yaml: return yaml.safe_load(txt)
    cfg={}
    for line in txt.splitlines():
        if ':' in line and not line.strip().startswith('#'):
            k,v=line.split(':',1); cfg[k.strip()]=v.strip()
    return cfg
def make_ctx(verify: bool, cafile: str|None):
    if verify:
        if cafile and Path(cafile).exists(): return ssl.create_default_context(cafile=str(cafile))
        return ssl.create_default_context()
    return ssl._create_unverified_context()
def main():
    import argparse
    ap=argparse.ArgumentParser()
    ap.add_argument('--config', default='config/email_watch.yaml')
    ap.add_argument('--insecure', action='store_true', help='disable TLS verification (diagnostic only)')
    a=ap.parse_args()
    cfg = load_cfg(Path(a.config))
    host = cfg.get('host'); port=int(cfg.get('port',993)); user=cfg.get('username'); pwd=cfg.get('password')
    verify = bool(cfg.get('verify_ssl', True)) and not a.insecure
    cafile = cfg.get('cafile') or None
    print(f"Connecting to {host}:{port} as {user} (verify_ssl={'on' if verify else 'OFF'})")
    ctx=make_ctx(verify, cafile)
    with imaplib.IMAP4_SSL(host, port, ssl_context=ctx) as M:
        print("Server greeting:", M.welcome.decode('utf-8','ignore'))
        try: code, data = M.login(user, pwd); print("LOGIN:", code, data)
        except imaplib.IMAP4.error as e: print("LOGIN FAILED:", e); sys.exit(2)
        code, caps = M.capability(); print("CAPABILITY:", code, caps); M.logout()
    print("OK"); return 0
if __name__=='__main__': sys.exit(main())
