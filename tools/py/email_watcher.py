
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PersistentAssistant: Email watcher (IMAP)

Responsibilities
----------------
- Load config from config/email_watch.yaml
- Connect to an IMAP server (Gmail/Outlook/etc.) with TLS handling controlled by
  verify_ssl and cafile.
- Locate candidate messages based on allow_from and subject_flag (prefers UNSEEN).
- Download only .zip attachments into save_dir.
- Optionally run tools/ps1/apply_inbox.ps1 to apply packs.
- Move processed zips to processed_dir.
- Log activity to reports/ops/email_watch.log.

Notes
-----
- If your environment has SSL interception (AV proxy), set verify_ssl: false
  temporarily or point cafile at a trusted PEM bundle.
- Keep email_watch.yaml out of version control; it can contain credentials.
"""

import email
import imaplib
import os
import ssl
import sys
import time
import shutil
import subprocess
from pathlib import Path
from typing import List, Optional

try:
    import yaml  # Optional; we have a fallback parser
except Exception:
    yaml = None

# ------------------------------ Logging ---------------------------------

def _log_path(root: Path) -> Path:
    p = root / "reports" / "ops" / "email_watch.log"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p

def log_write(root: Path, msg: str) -> None:
    ts = time.strftime("%Y-%m-%d %H:%M:%S ")
    with open(_log_path(root), "a", encoding="utf-8") as f:
        f.write(ts + msg + "\n")

# ------------------------------ Config ----------------------------------

class WatchCfg:
    def __init__(self, d: dict):
        self.enabled            = bool(d.get("enabled", False))
        self.protocol           = str(d.get("protocol", "imap")).lower()
        self.host               = str(d.get("host", ""))
        self.port               = int(d.get("port", 993))
        self.username           = str(d.get("username", ""))
        self.password           = str(d.get("password", ""))
        self.folder             = str(d.get("folder", "INBOX"))
        self.allow_from         = [str(x).lower() for x in (d.get("allow_from") or [])]
        self.subject_flag       = str(d.get("subject_flag", "[PA] APPLY"))
        self.save_dir           = str(d.get("save_dir", "_inbox"))
        self.processed_dir      = str(d.get("processed_dir", "_inbox/processed"))
        self.apply_after_download = bool(d.get("apply_after_download", True))
        self.verify_ssl         = bool(d.get("verify_ssl", True))
        self.cafile             = str(d.get("cafile", ""))

def load_yaml(path: Path) -> dict:
    txt = path.read_text(encoding="utf-8")
    if yaml:
        return yaml.safe_load(txt) or {}
    # Minimal fallback (key: "value" or key: value)
    out = {}
    for line in txt.splitlines():
        s = line.strip()
        if not s or s.startswith("#") or ":" not in s:
            continue
        k, v = line.split(":", 1)
        v = v.strip()
        if v[:1] in ("'", '"') and v[-1:] in ("'", '"'):
            v = v[1:-1]
        out[k.strip()] = v
    return out

# --------------------------- Repo root ----------------------------------

def resolve_repo_root(cli: str = "") -> Optional[Path]:
    """
    Prefer tools/py/apply_common.resolve_repo_root if available; else walk up.
    """
    if cli:
        p = Path(cli)
        if (p / ".git").exists():
            return p
    # Try import helper
    sys.path.append(str(Path(__file__).resolve().parent.parent))
    try:
        from apply_common import resolve_repo_root as _r  # type: ignore
        r = _r(cli)
        if r:
            return Path(r)
    except Exception:
        pass
    # Fallback: walk up
    p = Path(__file__).resolve()
    for _ in range(8):
        if (p / ".git").exists():
            return p
        p = p.parent
    return None

# ----------------------------- IMAP -------------------------------------

def build_ssl_context(verify_ssl: bool, cafile: str) -> ssl.SSLContext:
    if not verify_ssl:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx
    if cafile:
        return ssl.create_default_context(cafile=cafile)
    return ssl.create_default_context()

def imap_connect(host: str, port: int, ctx: ssl.SSLContext) -> imaplib.IMAP4_SSL:
    M = imaplib.IMAP4_SSL(host, port, ssl_context=ctx)
    typ, _ = M.noop()
    if typ != "OK":
        raise RuntimeError("IMAP NOOP failed before login")
    return M

def imap_login(M: imaplib.IMAP4_SSL, username: str, password: str) -> None:
    typ, data = M.login(username, password)
    if typ != "OK":
        raise RuntimeError(f"LOGIN failed: {data!r}")

def imap_select(M: imaplib.IMAP4_SSL, folder: str) -> None:
    typ, _ = M.select(folder, readonly=False)
    if typ != "OK":
        raise RuntimeError(f"Could not select folder: {folder}")

# --------------------------- Helpers ------------------------------------

def _normalize_addr(s: str) -> str:
    try:
        from email.utils import parseaddr
        _, addr = parseaddr(s or "")
        return (addr or "").lower()
    except Exception:
        return (s or "").lower()

def _message_matches(msg: email.message.Message, allow_from: List[str], subject_flag: str) -> bool:
    subj = (msg.get("Subject") or "")
    if subject_flag and subject_flag not in subj:
        return False
    if allow_from:
        cand = _normalize_addr(msg.get("From") or msg.get("Sender") or msg.get("Delivered-To") or "")
        if cand not in allow_from:
            return False
    return True

def _iter_candidate_uids(M: imaplib.IMAP4_SSL) -> List[bytes]:
    # Prefer unseen to avoid reprocessing; else last 50
    typ, data = M.uid("search", None, "(UNSEEN)")
    if typ == "OK" and data and data[0]:
        return data[0].split()
    typ, data = M.uid("search", None, "ALL")
    if typ != "OK" or not data or not data[0]:
        return []
    return data[0].split()[-50:]

def download_zip_attachments(root: Path, M: imaplib.IMAP4_SSL, cfg: WatchCfg) -> int:
    save_dir = root / cfg.save_dir
    save_dir.mkdir(parents=True, exist_ok=True)
    total_saved = 0

    for uid in _iter_candidate_uids(M):
        typ, data = M.uid("fetch", uid, "(RFC822)")
        if typ != "OK" or not data or not data[0]:
            continue
        raw = data[0][1]
        msg = email.message_from_bytes(raw)

        if not _message_matches(msg, cfg.allow_from, cfg.subject_flag):
            continue

        saved_this_msg = 0
        for part in msg.walk():
            if part.get_content_maintype() == "multipart":
                continue
            cd = (part.get("Content-Disposition") or "")
            if "attachment" not in cd.lower():
                continue
            fn = part.get_filename()
            if not fn or not fn.lower().endswith(".zip"):
                continue
            payload = part.get_payload(decode=True) or b""
            if not payload:
                continue

            out = save_dir / fn
            i = 1
            while out.exists():
                out = save_dir / f"{out.stem}_{i}{out.suffix}"
                i += 1
            out.write_bytes(payload)
            saved_this_msg += 1
            log_write(root, f"saved {out} from '{msg.get('From','')}' subj='{msg.get('Subject','')}'")

        if saved_this_msg > 0:
            total_saved += saved_this_msg
            M.uid("store", uid, "+FLAGS", r"(\Seen)")

    return total_saved

# ------------------------ Local processing -------------------------------

def process_local(cfg: WatchCfg, root: Path) -> int:
    inbox = root / cfg.save_dir
    processed = root / cfg.processed_dir
    inbox.mkdir(parents=True, exist_ok=True)
    processed.mkdir(parents=True, exist_ok=True)
    zips = sorted(inbox.glob("*.zip"))
    if not zips:
        log_write(root, "no local zips to process")
        return 0

    for zp in zips:
        if os.environ.get("PA_DRY_RUN") == "1":
            log_write(root, f"dry-run: would apply {zp}")
        elif cfg.apply_after_download:
            ps1 = root / "tools" / "ps1" / "apply_inbox.ps1"
            if ps1.exists():
                subprocess.call(["pwsh", "-File", str(ps1)], cwd=str(root))

        dest = processed / zp.name
        i = 1
        while dest.exists():
            dest = processed / f"{dest.stem}_{i}{dest.suffix}"
            i += 1
        shutil.move(str(zp), str(dest))
        log_write(root, f"moved to {dest}")

    return 0

# -------------------------------- CLI -----------------------------------

def main() -> int:
    import argparse
    ap = argparse.ArgumentParser(description="PersistentAssistant IMAP email watcher")
    ap.add_argument("--repo-root", default="", help="explicit repo root (optional)")
    ap.add_argument("--process-local", action="store_true", help="process local zips only")
    ap.add_argument("--insecure", action="store_true", help="disable TLS verification for this run")
    args = ap.parse_args()

    root = resolve_repo_root(args.repo_root)
    if not root:
        print("Repo root not found", file=sys.stderr)
        return 2

    cfg_path = root / "config" / "email_watch.yaml"
    if not cfg_path.exists():
        print(f"missing config: {cfg_path}", file=sys.stderr)
        return 2
    cfg = WatchCfg(load_yaml(cfg_path))

    if args.process_local:
        return process_local(cfg, root)

    if not cfg.enabled:
        print("watcher disabled; exiting 0")
        return 0

    try:
        ctx = build_ssl_context(verify_ssl=(cfg.verify_ssl and not args.insecure), cafile=cfg.cafile)
        M = imap_connect(cfg.host, cfg.port, ctx)
    except ssl.SSLError as e:
        log_write(root, f"TLS error: {e!s}")
        print(f"TLS error: {e!s}", file=sys.stderr)
        return 3
    except Exception as e:
        log_write(root, f"connect error: {e!s}")
        print(f"connect error: {e!s}", file=sys.stderr)
        return 3

    try:
        imap_login(M, cfg.username, cfg.password)
    except Exception as e:
        log_write(root, f"login error: {e!s}")
        print(f"login error: {e!s}", file=sys.stderr)
        try:
            M.logout()
        except Exception:
            pass
        return 4

    try:
        imap_select(M, cfg.folder)
        saved = download_zip_attachments(root, M, cfg)
    finally:
        try:
            M.close()
        except Exception:
            pass
        try:
            M.logout()
        except Exception:
            pass

    if saved == 0:
        log_write(root, "no qualifying messages")
        return 0
    return process_local(cfg, root)

if __name__ == "__main__":
    sys.exit(main())
