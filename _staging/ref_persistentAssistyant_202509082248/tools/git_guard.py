# =============================================================================
# File: tools/git_guard.py
# Persistent Assistant v3 – Git Guard (status / ensure clean / commit / push)
# Author: G. Rapson | GR-Analysis
# Created: 2025-08-19 15:40 BST
# Update History:
#   - 2025-08-19 15:40 BST: Initial version with status/ensure/commit/push and JSON SUMMARY.
# Lines: ~240 (functions: 10)
# =============================================================================

from __future__ import annotations
# --- PA_ROOT_IMPORT ---
import sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
# --- /PA_ROOT_IMPORT ---

import os
import sys
import json
import argparse
import subprocess
import datetime

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LOG_DIR = os.path.join(PROJECT_ROOT, "logs")
os.makedirs(LOG_DIR, exist_ok=True)
RUN_LOG = os.path.join(LOG_DIR, f"git_guard_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

# ---------- utilities ----------

def _log(msg: str):
    try:
        with open(RUN_LOG, "a", encoding="utf-8") as f:
            f.write(msg + "\n")
    except Exception:
        pass

def _run_git(args: list[str], cwd: str = PROJECT_ROOT) -> tuple[int, str, str]:
    cmd = ["git"] + args
    _log(f"CMD: {' '.join(cmd)}")
    try:
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=False)
        out = p.stdout or ""
        err = p.stderr or ""
        _log(f"RC={p.returncode}\n-- STDOUT --\n{out}\n-- STDERR --\n{err}")
        return p.returncode, out, err
    except Exception as e:
        _log(f"EXC: {e}")
        return 1, "", str(e)

def _parse_porcelain(porcelain: str) -> dict:
    """
    Git porcelain format: XY <path>
    X = index status (staged), Y = worktree status (unstaged)
    '??' = untracked
    """
    staged = unstaged = untracked = 0
    lines = [ln for ln in porcelain.splitlines() if ln.strip()]
    for ln in lines:
        if ln.startswith("??"):
            untracked += 1
        else:
            if len(ln) >= 2:
                x, y = ln[0], ln[1]
                if x != " ":
                    staged += 1
                if y != " ":
                    unstaged += 1
    return {"staged": staged, "unstaged": unstaged, "untracked": untracked, "entries": len(lines)}

def _ahead_behind() -> tuple[int, int, str]:
    rc, out, _ = _run_git(["status", "-sb"])
    branch = "unknown"
    ahead = behind = 0
    if rc == 0 and out:
        # Example: "## main...origin/main [ahead 1, behind 0]"
        first = out.splitlines()[0].strip()
        branch = first.replace("## ", "").split()[0]
        if "[" in first and "]" in first:
            inside = first[first.find("[")+1:first.find("]")]
            parts = inside.split(",")
            for p in parts:
                p = p.strip()
                if p.startswith("ahead "):
                    try: ahead = int(p.split()[1])
                    except: pass
                if p.startswith("behind "):
                    try: behind = int(p.split()[1])
                    except: pass
    return ahead, behind, branch

def _current_branch() -> str:
    rc, out, _ = _run_git(["rev-parse", "--abbrev-ref", "HEAD"])
    return out.strip() if rc == 0 else "unknown"

def _ensure_repo() -> bool:
    rc, _, _ = _run_git(["rev-parse", "--git-dir"])
    return rc == 0

# ---------- operations ----------

def git_status() -> dict:
    ok_repo = _ensure_repo()
    if not ok_repo:
        return {"ok": False, "error": "Not a git repository", "root": PROJECT_ROOT}

    rc_p, out_p, _ = _run_git(["status", "--porcelain"])
    counts = _parse_porcelain(out_p if rc_p == 0 else "")

    ahead, behind, branch_sb = _ahead_behind()
    rc_b, out_b, _ = _run_git(["rev-parse", "--abbrev-ref", "HEAD"])
    branch = out_b.strip() if rc_b == 0 else branch_sb

    dirty = (counts["staged"] + counts["unstaged"] + counts["untracked"]) > 0
    summary = {
        "ok": True,
        "root": PROJECT_ROOT.replace("\\", "/"),
        "branch": branch,
        "ahead": ahead,
        "behind": behind,
        "dirty": dirty,
        "counts": counts
    }
    return summary

def git_commit(message: str, include_untracked: bool = True, push: bool = False) -> dict:
    if not _ensure_repo():
        return {"ok": False, "error": "Not a git repository"}

    add_args = ["add", "-A"] if include_untracked else ["add", "-u"]
    rc_a, _, err_a = _run_git(add_args)
    if rc_a != 0:
        return {"ok": False, "error": f"git add failed: {err_a}"}

    rc_d, out_d, _ = _run_git(["diff", "--cached", "--name-only"])
    changed = [ln for ln in (out_d or "").splitlines() if ln.strip()]
    if not changed:
        return {"ok": False, "error": "Nothing to commit (index empty)"}

    rc_c, _, err_c = _run_git(["commit", "-m", message])
    if rc_c != 0:
        return {"ok": False, "error": f"git commit failed: {err_c}"}

    pushed = False
    if push:
        rc_p, _, err_p = _run_git(["push"])
        if rc_p != 0:
            return {"ok": True, "committed": True, "pushed": False, "warning": f"git push failed: {err_p}"}
        pushed = True

    st = git_status()
    st.update({"ok": True, "committed": True, "pushed": pushed, "changed_files": changed})
    return st

def ensure_clean(fail_message: str | None = None) -> dict:
    st = git_status()
    if not st.get("ok"):
        return st
    if st.get("dirty"):
        return {
            "ok": False,
            "error": fail_message or "Working tree is dirty",
            "status": st
        }
    return {"ok": True, "status": st}

# ---------- CLI ----------

def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Git Guard: status / ensure clean / commit / push")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--status", action="store_true", help="Print status and exit")
    g.add_argument("--ensure-clean", action="store_true", help="Exit nonzero if working tree is dirty")
    g.add_argument("--commit", action="store_true", help="Commit current changes")
    ap.add_argument("-m", "--message", default="", help="Commit message (required with --commit)")
    ap.add_argument("--no-untracked", action="store_true", help="Do not add untracked files on commit")
    ap.add_argument("--push", action="store_true", help="Push after commit")
    ap.add_argument("--reason", default="", help="Reason (annotate logs/commit)")
    args = ap.parse_args(argv)

    _log(f"MODE: {'status' if args.status else 'ensure-clean' if args.ensure_clean else 'commit'}")
    _log(f"ARGS: {args}")

    if args.status:
        res = git_status()
        print("SUMMARY:", json.dumps(res))
        return 0 if res.get("ok", False) else 1

    if args.ensure_clean:
        res = ensure_clean(args.reason or "Dirty tree")
        print("SUMMARY:", json.dumps(res))
        return 0 if res.get("ok", False) else 1

    if args.commit:
        if not args.message:
            # build a default message with timestamp and optional reason
            ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            args.message = f"chore: checkpoint ({ts})"
            if args.reason:
                args.message += f" — {args.reason}"

        res = git_commit(
            message=args.message,
            include_untracked=(not args.no_untracked),
            push=args.push
        )
        print("SUMMARY:", json.dumps(res))
        return 0 if res.get("ok", False) else 1

    return 2

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
