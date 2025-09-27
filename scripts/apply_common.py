import subprocess, sys
from pathlib import Path

def run(args, check=True, cwd=None):
    subprocess.run(args, cwd=cwd, check=check)

def have_git_repo(root: Path) -> bool:
    return (root / '.git').exists()

def ensure_pydeps(mods):
    for m in mods:
        try:
            __import__(m)
        except Exception:
            subprocess.run([sys.executable,'-m','pip','install',m], check=True)

def git(args, root: Path, allow_fail=False):
    try:
        run(['git']+list(args), cwd=root, check=not allow_fail)
        return 0
    except subprocess.CalledProcessError as e:
        if allow_fail:
            return e.returncode or 1
        raise

def zip_files(out_zip: Path, files, root: Path):
    from zipfile import ZipFile, ZIP_DEFLATED
    out_zip.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(out_zip,'w',compression=ZIP_DEFLATED) as z:
        for f in files:
            from pathlib import Path as _P
            f=_P(f)
            if f.exists(): z.write(f, f.relative_to(root).as_posix())
