# tools/py/agentic/patch_utils.py
import os, io, hashlib, fnmatch

def ensure_dir(p: str):
    os.makedirs(p, exist_ok=True)

def sha256_hex(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()

def path_allowed(path: str, allow_globs, deny_globs) -> bool:
    pn = path.replace("\\", "/")
    if any(fnmatch.fnmatch(pn, g) for g in deny_globs or []):
        return False
    if not allow_globs:
        return True
    return any(fnmatch.fnmatch(pn, g) for g in allow_globs)

def make_backup(src: str, backups_dir: str) -> str:
    ensure_dir(backups_dir)
    base = os.path.basename(src)
    out = os.path.join(backups_dir, base + ".bak")
    i = 1
    while os.path.exists(out):
        out = os.path.join(backups_dir, f"{base}.bak.{i}")
        i += 1
    with open(src, "rb") as r, open(out, "wb") as w:
        w.write(r.read())
    return out

def apply_append(path: str, content: str):
    with open(path, "ab") as f:
        data = content.encode("utf-8")
        if not content.endswith("\n"):
            data += b"\n"
        f.write(data)

def apply_replace(path: str, content: str):
    with open(path, "wb") as f:
        f.write(content.encode("utf-8"))

def apply_unified_diff(_path: str, _diff_text: str):
    # Keep minimal for now.
    # We’ll add a robust patcher (python-patch style) in a follow-up.
    raise NotImplementedError("mode='patch' not implemented in minimal bootstrap")
