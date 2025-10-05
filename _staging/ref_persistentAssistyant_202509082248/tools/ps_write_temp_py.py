from __future__ import annotations
import pathlib, time, random, string, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
TMP = ROOT / "tmp" / "snippets"
TMP.mkdir(parents=True, exist_ok=True)

def random_tag(n=6):
    import secrets, string
    alphabet = string.ascii_lowercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(n))

def write_temp_py(content: str, prefix="snippet"):
    tag = random_tag()
    p = TMP / f"{prefix}_{tag}.py"
    p.write_text(content, encoding="utf-8")
    return p

def run_temp_py(content: str, prefix="snippet", check=True):
    p = write_temp_py(content, prefix=prefix)
    try:
        r = subprocess.run([sys.executable, str(p)], capture_output=True, text=True)
        if check and r.returncode != 0:
            raise RuntimeError(f"Temp script failed (rc={r.returncode}):\nSTDOUT:\n{r.stdout}\nSTDERR:\n{r.stderr}")
        return r
    finally:
        # keep file for debugging; a cleaner may archive/purge later
        pass

if __name__ == "__main__":
    s = "print('ps_write_temp_py OK')"
    out = run_temp_py(s, check=True)
    print(out.stdout.strip())
