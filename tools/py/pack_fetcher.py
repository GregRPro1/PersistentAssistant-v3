#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pack Fetcher (GitHub/URL) for PersistentAssistant
- Polls GitHub Releases OR uses control/next_pack.json with a direct URL or tag
- Downloads latest pack zip (+ optional .sha256), verifies
- Saves to _inbox, optionally runs tools/ps1/apply_inbox.ps1, archives processed
- Logs to reports/ops/pack_fetcher.log
"""
import json, os, sys, time, ssl, hashlib, fnmatch
from pathlib import Path
from typing import Optional, Dict, Any
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

try:
    import yaml
except Exception:
    yaml = None

LOG_NAME = "pack_fetcher.log"

# ---------------- Logging ----------------
def _log_path(root: Path) -> Path:
    p = root / "reports" / "ops" / LOG_NAME
    p.parent.mkdir(parents=True, exist_ok=True); return p

def log(root: Path, msg: str) -> None:
    ts = time.strftime("%Y-%m-%d %H:%M:%S ")
    with open(_log_path(root), "a", encoding="utf-8") as f:
        f.write(ts + msg + "\n")

# ---------------- Common -----------------
def resolve_repo_root(cli: str = "") -> Optional[Path]:
    if cli:
        p = Path(cli)
        if (p / ".git").exists():
            return p
    # try helper
    sys.path.append(str(Path(__file__).resolve().parent.parent))
    try:
        from apply_common import resolve_repo_root as _r  # type: ignore
        r = _r(cli)
        if r:
            return Path(r)
    except Exception:
        pass
    # fallback
    p = Path(__file__).resolve()
    for _ in range(8):
        if (p / ".git").exists():
            return p
        p = p.parent
    return None

def load_yaml(p: Path) -> Dict[str, Any]:
    txt = p.read_text(encoding="utf-8")
    if yaml:
        return yaml.safe_load(txt) or {}
    out = {}
    for line in txt.splitlines():
        s = line.strip()
        if not s or s.startswith("#") or ":" not in s:
            continue
        k, v = line.split(":", 1)
        out[k.strip()] = v.strip().strip("'").strip('"')
    return out

def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()

def write_bytes(p: Path, data: bytes) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "wb") as f:
        f.write(data)

# ---------------- HTTP -------------------
def http_get(url: str, headers: Optional[Dict[str, str]] = None, verify_ssl: bool = True) -> bytes:
    req = Request(url, headers=headers or {})
    ctx = ssl.create_default_context()
    if not verify_ssl:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    with urlopen(req, context=ctx, timeout=60) as resp:
        return resp.read()

# --------------- GitHub ------------------
def gh_headers(pat: Optional[str]) -> Dict[str, str]:
    h = {"Accept": "application/vnd.github+json", "User-Agent": "PA-PackFetcher/1.0"}
    if pat:
        h["Authorization"] = f"token {pat}"
    return h

def gh_latest_release(api_base: str, owner: str, repo: str, pat: Optional[str], verify_ssl: bool) -> Dict[str, Any]:
    url = f"{api_base}/repos/{owner}/{repo}/releases/latest"
    data = http_get(url, headers=gh_headers(pat), verify_ssl=verify_ssl)
    return json.loads(data.decode("utf-8"))

def gh_release_by_tag(api_base: str, owner: str, repo: str, tag: str, pat: Optional[str], verify_ssl: bool) -> Dict[str, Any]:
    url = f"{api_base}/repos/{owner}/{repo}/releases/tags/{tag}"
    data = http_get(url, headers=gh_headers(pat), verify_ssl=verify_ssl)
    return json.loads(data.decode("utf-8"))

# --------------- Core --------------------
def download_to(root: Path, url: str, out_dir: Path, fname_hint: Optional[str], verify_ssl: bool) -> Path:
    data = http_get(url, verify_ssl=verify_ssl)
    name = fname_hint or Path(url).name or f"pack_{int(time.time())}.zip"
    out = out_dir / name
    i = 1
    while out.exists():
        out = out_dir / f"{Path(name).stem}_{i}{Path(name).suffix}"
        i += 1
    write_bytes(out, data)
    return out

def get_cfg(root: Path) -> Dict[str, Any]:
    p = root / "config" / "github_fetch.yaml"
    if not p.exists():
        raise FileNotFoundError(f"missing config: {p}")
    return load_yaml(p)

def load_control(root: Path) -> Optional[Dict[str, Any]]:
    p = root / "control" / "next_pack.json"
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None

def main() -> int:
    import argparse, subprocess
    ap = argparse.ArgumentParser(description="PA GitHub/URL pack fetcher")
    ap.add_argument("--repo-root", default="")
    ap.add_argument("--once", action="store_true", help="run one fetch cycle then exit")
    ap.add_argument("--interval", type=int, default=60, help="poll interval seconds")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    root = resolve_repo_root(args.repo_root)
    if not root:
        print("Repo root not found", file=sys.stderr); return 2

    cfg = get_cfg(root)
    if not cfg.get("enabled", False):
        log(root, "disabled; exiting 0"); return 0

    inbox = root / str(cfg.get("save_dir", "_inbox"))
    processed = root / str(cfg.get("processed_dir", "_inbox/processed"))
    inbox.mkdir(parents=True, exist_ok=True); processed.mkdir(parents=True, exist_ok=True)

    def cycle():
        try:
            control = load_control(root)
            verify_ssl = bool(cfg.get("verify_ssl", True))
            if control and str(control.get("source")) == "url":
                url = str(control.get("url", ""))
                if not url:
                    log(root, "control url missing"); return
                name = control.get("name") or None
                if args.dry_run:
                    log(root, f"[dry] would download {url}"); return
                zp = download_to(root, url, inbox, name, verify_ssl)
                log(root, f"downloaded {zp.name} from control url")
            else:
                owner = str(cfg.get("owner"))
                repo  = str(cfg.get("repo"))
                api   = str(cfg.get("api_base", "https://api.github.com")).rstrip("/")
                pat   = os.environ.get(str(cfg.get("pat_env_var","PA_GITHUB_PAT")), "")
                asset_glob = str(cfg.get("asset_name_glob", "PA_OUTPUT_*.zip"))
                tag = None
                if control and control.get("source") == "release" and control.get("tag"):
                    tag = str(control.get("tag"))
                    rel = gh_release_by_tag(api, owner, repo, tag, pat, verify_ssl)
                else:
                    rel = gh_latest_release(api, owner, repo, pat, verify_ssl)
                    tag = rel.get("tag_name")

                assets = rel.get("assets") or []
                zip_asset = None; sha_asset = None
                for a in assets:
                    n = a.get("name","")
                    if fnmatch.fnmatch(n, asset_glob): zip_asset = a
                    if n.endswith(".sha256"): sha_asset = a
                if not zip_asset:
                    log(root, f"no asset matching {asset_glob} on release {tag}"); return

                if args.dry_run:
                    log(root, f"[dry] would fetch asset {zip_asset.get('name')} from release {tag}"); return

                zp_url = zip_asset.get("browser_download_url")
                sha_txt = None
                if sha_asset:
                    try:
                        sha_txt = http_get(sha_asset.get("browser_download_url"), headers=gh_headers(pat), verify_ssl=verify_ssl).decode("utf-8","ignore")
                    except Exception as e:
                        log(root, f"sha256 fetch error: {e!s}")

                zp = download_to(root, zp_url, inbox, zip_asset.get("name"), verify_ssl)
                log(root, f"downloaded {zp.name} from release {tag}")

                if sha_txt:
                    want = sha_txt.strip().split()[0]
                    have = sha256_file(zp)
                    if want and want != have:
                        log(root, f"sha256 mismatch want={want} have={have}; moving to processed_bad")
                        bad = processed / ("BAD_"+zp.name); zp.rename(bad); return
                    log(root, f"sha256 OK {want}")

            # Apply local inbox if configured
            if bool(cfg.get("apply_after_download", True)) and os.environ.get("PA_DRY_RUN") != "1":
                ps1 = root / "tools" / "ps1" / "apply_inbox.ps1"
                if ps1.exists():
                    subprocess.call(["pwsh","-File",str(ps1)], cwd=str(root))

        except HTTPError as e:
            log(root, f"http {e.code}: {e.reason}")
        except URLError as e:
            log(root, f"url error: {e.reason}")
        except Exception as e:
            log(root, f"error: {e!s}")

    if args.once:
        cycle(); return 0

    # poll loop
    while True:
        cycle()
        time.sleep(max(10, int(args.interval)))

if __name__ == "__main__":
    sys.exit(main())