from __future__ import annotations
# --- PA_ROOT_IMPORT ---
import sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
# --- /PA_ROOT_IMPORT ---
import os, sys, time, shutil, subprocess, zipfile, pathlib, json
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parents[1]
TMP = ROOT / "tmp"
ARCHIVE = TMP / "archive"
FEEDBACK = TMP / "feedback"
INSIGHTS = ROOT / "data" / "insights"
REPL_LOG = INSIGHTS / "replace_log.txt"

def ts(): return datetime.now(timezone.utc).isoformat()

def run(cmd: list[str], check=True) -> tuple[int,str,str]:
    p = subprocess.run(cmd, capture_output=True, text=True)
    if check and p.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(cmd)}\n{p.stdout}\n{p.stderr}")
    return p.returncode, p.stdout.strip(), p.stderr.strip()

def file_sha(path: pathlib.Path) -> str:
    import hashlib
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1<<20), b""):
            h.update(chunk)
    return h.hexdigest()

def log_replace(msg: str):
    REPL_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(REPL_LOG, "a", encoding="utf-8") as f:
        f.write(f"[{ts()}] {msg}\n")
    print(msg)

def tidy_tmp(retain_candidates: bool = True, purge_days: int = 7):
    ARCHIVE.mkdir(parents=True, exist_ok=True)
    cand_dir = ARCHIVE / "candidates"
    cand_dir.mkdir(parents=True, exist_ok=True)
    now = time.time()
    for f in TMP.iterdir():
        if f.is_dir() and f.name in ("feedback","archive","prep_next"): 
            continue
        if ".bak." in f.name or ".reject." in f.name:
            shutil.move(str(f), str(ARCHIVE / f.name)); continue
        if f.suffix in (".py",".yaml") and f.name != "last_summary.txt":
            if retain_candidates:
                shutil.copy2(str(f), str(cand_dir / f.name))
            else:
                shutil.move(str(f), str(cand_dir / f.name))
    for f in ARCHIVE.glob("**/*"):
        if f.is_file():
            age_days = (now - f.stat().st_mtime)/86400.0
            if age_days > purge_days and f.suffix.lower() != ".zip":
                try: f.unlink()
                except: pass

def pack_feedback(tag: str, extras: dict[str, str]) -> pathlib.Path:
    FEEDBACK.mkdir(parents=True, exist_ok=True)
    zpath = FEEDBACK / f"pack_{tag}_{time.strftime('%Y%m%d_%H%M%S')}.zip"
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        if INSIGHTS.exists():
            for f in INSIGHTS.glob("*"):
                z.write(f, f"insights/{f.name}")
        for name, path in extras.items():
            if name.startswith("_"): continue
            if path and os.path.exists(path):
                z.write(path, name)
        rep_dir = extras.get("_replaced_dir")
        rep_base = extras.get("_replaced_base")
        if rep_dir and rep_base and os.path.isdir(rep_dir):
            for fn in os.listdir(rep_dir):
                if fn.startswith(rep_base + ".bak.") or fn.startswith(rep_base + ".reject."):
                    z.write(os.path.join(rep_dir, fn), f"replaced_artifacts/{fn}")
    return zpath

def main():
    # Modes:
    #   apply_and_pack.py <target> <new> [label]
    #   apply_and_pack.py                (pack only)
    label = None
    target = None
    newf = None
    if len(sys.argv) >= 3:
        target = pathlib.Path(sys.argv[1])
        newf   = pathlib.Path(sys.argv[2])
        label  = sys.argv[3] if len(sys.argv) >= 4 else target.stem
    else:
        label = "apply_pack"

    # 0) snapshot step state
    try:
        rc, step_out, _ = run([sys.executable, "tools/show_next_step.py"], check=False)
    except Exception as e:
        step_out = f"[ERROR] show_next_step failed: {e}"
    (TMP / "current_step.txt").write_text(step_out, encoding="utf-8")

    # 1) pre-inventory
    try: run([sys.executable, "tools/deep_inventory.py"], check=False)
    except Exception: pass

    replaced_ok = False
    attempted = False
    # 2) guarded replace if target/new provided
    if target is not None and newf is not None:
        attempted = True
        if not target.exists():
            log_replace(f"SKIP: target missing -> {target}")
        elif not newf.exists():
            log_replace(f"SKIP: new file missing -> {newf}")
        else:
            expected = file_sha(target)
            rc, out, err = run([sys.executable, "tools/safe_replace.py",
                                "--path", str(target),
                                "--expected-sha", expected,
                                "--new", str(newf)], check=False)
            if rc == 0:
                replaced_ok = True
                log_replace(f"OK: replaced {target}")
            else:
                log_replace(f"SKIP: replace failed for {target} (see .reject/.bak)")
    else:
        log_replace("SKIP: replace not attempted (pack-only mode)")

    # 3) post-inventory
    try: run([sys.executable, "tools/deep_inventory.py"], check=False)
    except Exception: pass

    # 4) summary + clipboard (best-effort)
    try: run([sys.executable, "tools/make_summary.py"], check=False)
    except Exception: pass

    # 5) tidy + pack
    tidy_tmp(retain_candidates=True)
    extras = {
        "current_step.txt": str(TMP / "current_step.txt"),
    }
    if target is not None:
        extras["_replaced_dir"] = str(target.parent)
        extras["_replaced_base"] = target.name
        if newf is not None:
            extras[f"candidate/{newf.name}"] = str(newf)
    pack = pack_feedback(label or "apply_pack", extras)
    print(f"[APPLY+PACK {'OK' if replaced_ok else 'WARN'}] {pack}")

    sys.exit(0 if replaced_ok or not attempted else 1)

if __name__ == "__main__":
    main()
