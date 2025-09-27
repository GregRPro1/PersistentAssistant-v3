import os, sys, imaplib, email, time, shutil, subprocess, ssl
from pathlib import Path
try:
    import yaml
except Exception:
    yaml=None
def load_cfg(path: Path):
    if not path.exists():
        return {'enabled': False,'save_dir': '_inbox','processed_dir': '_inbox/processed','apply_after_download': False,'verify_ssl': True,'cafile': ''}
    txt = path.read_text(encoding='utf-8')
    if yaml: return yaml.safe_load(txt)
    cfg = {}
    for line in txt.splitlines():
        if ':' in line and not line.strip().startswith('#'):
            k,v=line.split(':',1); cfg[k.strip()]=v.strip().strip('"').strip("'")
    return cfg
def build_ssl_context(cfg):
    verify = str(cfg.get('verify_ssl', True)).lower() != 'false' and os.environ.get('PA_INSECURE_SSL') != '1'
    cafile = cfg.get('cafile') or ''
    if verify:
        if cafile and Path(cafile).exists(): return ssl.create_default_context(cafile=str(cafile))
        return ssl.create_default_context()
    else:
        return ssl._create_unverified_context()
def safe_fn(name: str) -> str: return "".join(c if c.isalnum() or c in "._-+" else "_" for c in name)
def log(path: Path, msg: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path,'a',encoding='utf-8') as f: f.write(time.strftime("%Y-%m-%d %H:%M:%S ") + msg + "\n")
def save_attachment(part, out_dir: Path, logf: Path):
    fn = part.get_filename(); if not fn: return None
    fn = safe_fn(email.utils.collapse_rfc2231_value(fn))
    data = part.get_payload(decode=True); if not data: return None
    out_dir.mkdir(parents=True, exist_ok=True); p = out_dir / fn; i=1
    while p.exists(): p = out_dir / f"{p.stem}_{i}{p.suffix}"; i+=1
    p.write_bytes(data); log(logf, f"saved {p}"); return p
def process_local(cfg, repo: Path, logf: Path):
    inbox = repo / cfg.get('save_dir','_inbox'); processed = repo / cfg.get('processed_dir','_inbox/processed')
    inbox.mkdir(parents=True, exist_ok=True); processed.mkdir(parents=True, exist_ok=True)
    zips = sorted(inbox.glob("*.zip"))
    if not zips: log(logf, "no local zips to process"); return 0
    for zp in zips:
        apply_zip = True if str(cfg.get('apply_after_download', True)).lower()=='true' else False
        if os.environ.get('PA_DRY_RUN')=='1':
            log(logf, f"dry-run: would apply {zp}")
        elif apply_zip:
            ps1 = repo / 'tools' / 'ps1' / 'apply_inbox.ps1'
            if ps1.exists(): subprocess.call(['pwsh','-File', str(ps1)], cwd=repo)
            else: subprocess.call(['pwsh','-File', str(repo/'apply_packs_only.ps1'), '-ZipPath', str(zp)], cwd=repo)
        dest = processed / zp.name; i=1
        while dest.exists(): dest = processed / f"{dest.stem}_{i}{dest.suffix}"; i+=1
        shutil.move(str(zp), str(dest)); log(logf, f"moved to {dest}")
    return 0
def poll_imap(cfg, repo: Path, logf: Path):
    host = cfg.get('host'); user=cfg.get('username'); pwd=cfg.get('password')
    if not host or not user or not pwd: log(logf, "IMAP config incomplete; skipping"); return 0
    port = int(cfg.get('port', 993)); folder = cfg.get('folder','INBOX'); flag = cfg.get('subject_flag','[PA] APPLY')
    allow_from = set([s.lower() for s in cfg.get('allow_from', [])]); max_mb = int(cfg.get('max_attachment_mb', 50))
    save_dir = repo / cfg.get('save_dir','_inbox'); processed_dir = repo / cfg.get('processed_dir','_inbox/processed')
    save_dir.mkdir(parents=True, exist_ok=True); processed_dir.mkdir(parents=True, exist_ok=True)
    ctx = build_ssl_context(cfg)
    with imaplib.IMAP4_SSL(host, port, ssl_context=ctx) as M:
        M.login(user, pwd); M.select(folder)
        typ, data = M.search(None, 'UNSEEN')
        if typ!='OK': log(logf, f"search failed: {typ} {data}"); return 1
        for num in data[0].split():
            typ, msgdata = M.fetch(num, '(RFC822)'); if typ!='OK': continue
            msg = email.message_from_bytes(msgdata[0][1]); subj = msg.get('Subject',''); frm = email.utils.parseaddr(msg.get('From',''))[1].lower()
            if allow_from and frm not in allow_from: log(logf, f"skip email from {frm}"); continue
            if flag and flag not in subj: log(logf, f"skip email subj '{subj}' (missing flag)"); continue
            saved = []
            for part in msg.walk():
                if part.get_content_disposition()=='attachment':
                    fn = part.get_filename() or ''; if not fn.lower().endswith('.zip'): continue
                    payload = part.get_payload(decode=True) or b''; size = len(payload)/(1024*1024)
                    if size > max_mb: log(logf, f"skip {fn}: {size:.1f}MB > limit"); continue
                    p = save_attachment(part, save_dir, logf); 
                    if p: saved.append(p)
            M.store(num, '+FLAGS', '\\Seen')
            if saved: log(logf, f"saved {len(saved)} zip(s) from {frm} subj='{subj}'")
    return process_local(cfg, repo, logf)
def main():
    import argparse
    ap=argparse.ArgumentParser()
    ap.add_argument('--repo-root', default=''); ap.add_argument('--process-local', action='store_true')
    ap.add_argument('--insecure', action='store_true', help='override verify_ssl and disable TLS verification for this run')
    a=ap.parse_args()
    from apply_common import resolve_repo_root; repo = resolve_repo_root(a.repo_root)
    if not repo: print('Repo root not found', file=sys.stderr); return 2
    cfg = load_cfg(repo/'config'/'email_watch.yaml')
    if a.insecure: cfg['verify_ssl'] = False
    logf = repo/'reports'/'ops'/'email_watch.log'
    if a.process_local: return process_local(cfg, repo, logf)
    if not cfg.get('enabled'): print('email watcher disabled; exiting 0'); return 0
    try: return poll_imap(cfg, repo, logf)
    except Exception as e: log(logf, f"ERROR: {e}"); return 1
if __name__=='__main__': sys.exit(main())
