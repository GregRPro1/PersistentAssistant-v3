import os, sys, json, time, shutil
from pathlib import Path
import requests

try:
    import yaml
except Exception:
    yaml=None

try:
    import msal
except Exception:
    print("MSAL not installed. Run tools\\ps1\\install_deps.ps1", file=sys.stderr)
    sys.exit(3)

SCOPES = ["Mail.Read", "offline_access"]
GRAPH = "https://graph.microsoft.com/v1.0"

def load_yaml(path: Path):
    txt = path.read_text(encoding="utf-8")
    if yaml:
        return yaml.safe_load(txt)
    out={}
    for line in txt.splitlines():
        if ":" in line and not line.strip().startswith("#"):
            k,v=line.split(":",1); out[k.strip()]=v.strip().strip("'").strip('"')
    return out

def log_path(root: Path): 
    p = root/'reports'/'ops'/'email_watch_graph.log'
    p.parent.mkdir(parents=True, exist_ok=True); return p

def log(root: Path, msg: str):
    with open(log_path(root),'a',encoding='utf-8') as f:
        f.write(time.strftime("%Y-%m-%d %H:%M:%S ") + msg + "\n")

def process_local(cfg: dict, root: Path):
    inbox = root / cfg.get("save_dir","_inbox")
    processed = root / cfg.get("processed_dir","_inbox/processed")
    inbox.mkdir(parents=True, exist_ok=True)
    processed.mkdir(parents=True, exist_ok=True)
    zips = sorted(inbox.glob("*.zip"))
    if not zips:
        log(root, "no local zips to process"); return 0
    for zp in zips:
        apply_zip = str(cfg.get("apply_after_download", True)).lower()=='true'
        if os.environ.get("PA_DRY_RUN")=='1':
            log(root, f"dry-run: would apply {zp}")
        elif apply_zip:
            ps1 = root/'tools'/'ps1'/'apply_inbox.ps1'
            if ps1.exists():
                import subprocess
                subprocess.call(['pwsh','-File', str(ps1)], cwd=root)
        dest = processed / zp.name
        i=1
        while dest.exists():
            dest = processed / f"{dest.stem}_{i}{dest.suffix}"; i+=1
        shutil.move(str(zp), str(dest))
        log(root, f"moved to {dest}")
    return 0

def acquire_token(root: Path, cfg: dict, force_device: bool=False):
    authority = cfg.get("authority","https://login.microsoftonline.com/consumers")
    client_id = (cfg.get("client_id") or "").strip()
    if not client_id:
        log(root, "client_id missing in email_watch_graph.yaml"); sys.exit(2)
    cache_dir = root/'.secrets'; cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir/'msal_token_cache.bin'
    token_cache = msal.SerializableTokenCache()
    if cache_path.exists():
        try: token_cache.deserialize(cache_path.read_text())
        except Exception: pass
    app = msal.PublicClientApplication(client_id=client_id, authority=authority, token_cache=token_cache)
    result=None
    if not force_device:
        accts = app.get_accounts()
        if accts:
            result = app.acquire_token_silent(SCOPES, account=accts[0])
    if not result:
        flow = app.initiate_device_flow(scopes=SCOPES)
        if "user_code" not in flow:
            print("Device flow failed. Check app registration and 'Allow public client flows'.", file=sys.stderr); sys.exit(2)
        print("=== DEVICE LOGIN ===")
        print("Go to:", flow["verification_uri"])
        print("Enter code:", flow["user_code"])
        result = app.acquire_token_by_device_flow(flow)
    if "access_token" not in result:
        print("Auth failed:", result.get("error_description") or result, file=sys.stderr); sys.exit(2)
    cache_path.write_text(token_cache.serialize())
    return result["access_token"]

def gget(url, token, params=None, headers=None):
    h={"Authorization": f"Bearer {token}"}
    if headers: h.update(headers)
    r=requests.get(url, params=params, headers=h, timeout=30); r.raise_for_status(); return r.json()

def gpatch(url, token, body):
    h={"Authorization": f"Bearer {token}", "Content-Type":"application/json"}
    r=requests.patch(url, json=body, headers=h, timeout=30); r.raise_for_status(); return r.json() if r.content else {}

def download_zip_attachments(root: Path, token: str, cfg: dict):
    allow_from=set([s.lower() for s in cfg.get("allow_from",[])])
    subject_flag = (cfg.get("subject_flag") or "[PA]").strip()
    save_dir = root/cfg.get("save_dir","_inbox")
    save_dir.mkdir(parents=True, exist_ok=True)
    url = GRAPH + "/me/mailFolders/Inbox/messages"
    data = gget(url, token, params={"$top":"25","$select":"id,subject,from,isRead,hasAttachments,receivedDateTime","$filter":"isRead eq false","$orderby":"receivedDateTime desc"})
    msgs = data.get("value", [])
    saved=[]
    for m in msgs:
        subj = m.get("subject") or ""
        frm = (((m.get("from") or {}).get("emailAddress") or {}).get("address") or "").lower()
        if allow_from and frm not in allow_from: continue
        if subject_flag and subject_flag not in subj: continue
        mid=m["id"]
        at = gget(GRAPH+f"/me/messages/{mid}/attachments", token)
        any_saved=False
        for a in at.get("value",[]):
            if a.get("@odata.type")!="#microsoft.graph.fileAttachment": continue
            name=a.get("name","")
            if not name.lower().endswith(".zip"): continue
            cb=a.get("contentBytes"); if not cb: continue
            import base64; raw=base64.b64decode(cb)
            out = save_dir/name
            i=1
            while out.exists(): out = save_dir/f"{out.stem}_{i}{out.suffix}"; i+=1
            out.write_bytes(raw); saved.append(out); any_saved=True
            log(root, f"saved {out} from {frm} subj='{subj}'")
        if any_saved:
            try: gpatch(GRAPH+f"/me/messages/{mid}", token, {"isRead": True})
            except Exception: pass
    return saved

def main():
    import argparse
    ap=argparse.ArgumentParser()
    ap.add_argument("--repo-root", default="")
    ap.add_argument("--process-local", action="store_true")
    ap.add_argument("--device-login", action="store_true")
    a=ap.parse_args()

    # resolve repo root
    sys.path.append(str(Path(__file__).resolve().parent.parent))
    try:
        from apply_common import resolve_repo_root
    except Exception:
        def resolve_repo_root(_):
            p=Path(__file__).resolve()
            for _ in range(8):
                if (p/'.git').exists(): return p
                p=p.parent
            return None

    root = resolve_repo_root(a.repo_root)
    if not root:
        print("Repo root not found", file=sys.stderr); return 2

    cfg_path = root/'config'/'email_watch_graph.yaml'
    if not cfg_path.exists():
        print(f"missing config: {cfg_path}", file=sys.stderr); return 2
    cfg = load_yaml(cfg_path)

    if a.process_local: return process_local(cfg, root)
    if not cfg.get("enabled", False):
        print("graph watcher disabled; exiting 0"); return 0

    token = acquire_token(root, cfg, force_device=a.device_login)
    zips = download_zip_attachments(root, token, cfg)
    if zips: return process_local(cfg, root)
    log(root, "no qualifying messages"); return 0

if __name__=='__main__':
    sys.exit(main())
