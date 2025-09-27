import subprocess, sys, re
from pathlib import Path
def run(args, check=True, cwd=None): subprocess.run(args, cwd=cwd, check=check)
def have_git_repo(root: Path) -> bool: return (root / '.git').exists()
def ensure_pydeps(mods):
    for m in mods:
        try: __import__(m)
        except Exception: subprocess.run([sys.executable,'-m','pip','install',m], check=True)
def find_repo_root(start: Path):
    p=start
    for _ in range(10):
        if (p/'.git').exists(): return p
        if p.parent==p: break
        p=p.parent
    return None
def resolve_repo_root(cli_root: str | None):
    if cli_root:
        p=Path(cli_root)
        if have_git_repo(p): return p
    cand=find_repo_root(Path(__file__).resolve())
    if cand: return cand
    hard=Path(r'C:\_Repos\PersistentAssistant')
    return hard if have_git_repo(hard) else None
def git(args, root: Path, allow_fail=False):
    try: run(['git']+list(args), cwd=root, check=not allow_fail); return 0
    except subprocess.CalledProcessError as e:
        if allow_fail: return e.returncode or 1
        raise
def zip_files(out_zip: Path, files, root: Path):
    from zipfile import ZipFile, ZIP_DEFLATED
    out_zip.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(out_zip,'w',compression=ZIP_DEFLATED) as z:
        from pathlib import Path as _P
        for f in files:
            f=_P(f)
            if f.exists(): z.write(f, f.relative_to(root).as_posix())
_slug_re = re.compile(r'[^a-z0-9._/-]+')
def slugify_branch(text: str) -> str:
    s = text.lower()
    s = _slug_re.sub('-', s)
    s = s.strip('-/')
    s = re.sub(r'-+', '-', s)
    if s in ('.','..') or s.endswith('.lock'): s = s + '-x'
    return s[:48] or 'x'
