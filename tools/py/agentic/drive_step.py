import argparse
import subprocess
import sys
import os
from pathlib import Path
from typing import Optional, Dict, Any, List

try:
    import yaml
except Exception:
    yaml = None  # tests tolerate no-op if unavailable

def build_parser():
    p = argparse.ArgumentParser(prog="drive_step.py", allow_abbrev=False)
    p.add_argument("--step", required=True, help="Step id to run (e.g., 10.4)")
    p.add_argument("--apply", action="store_true", help="Apply changes")
    p.add_argument("--tests", type=str, default="tests", help="Pytest target (file/dir/node)")
    p.add_argument("--pytest-flags", nargs="*", metavar="PYTEST_FLAG", default=[],
                   help="Flags to pass to pytest, e.g. --pytest-flags -q -k smoke")
    p.add_argument("--retries", type=int, default=0, help="Retries on pytest failure")
    return p

def _run_pytest_subprocess(tests, flags):
    cmd = [sys.executable, "-m", "pytest", tests] + list(flags or [])
    return subprocess.run(cmd).returncode

# === Enhanced LEB runner: knows 'patch_apply' ==================================

def _run_patch_apply_inline(cmd: str) -> Dict[str, Any]:
    """
    Handle commands like:
      patch_apply --dry-run path.json
      patch_apply --apply path.json
    Returns leb_run-like dict: {ok, rc, stdout, stderr}
    """
    parts = cmd.strip().split()
    # minimal parse
    dry = True
    proposal = None
    for i, tok in enumerate(parts[1:]):
        if tok == "--apply":
            dry = False
        elif tok == "--dry-run":
            dry = True
        else:
            # first non-flag token after 'patch_apply' is treated as path
            proposal = tok if proposal is None else proposal
    if not proposal:
        return {"ok": False, "rc": 1, "stdout": "", "stderr": "no proposal path"}
    try:
        from tools.py.executor.patch_apply import apply_proposal
        res = apply_proposal(proposal_path=proposal, apply=not dry)
        import json as _j
        return {"ok": True, "rc": 0 if res.get("ok") else 1, "stdout": _j.dumps(res), "stderr": ""}
    except Exception as e:
        return {"ok": False, "rc": 1, "stdout": "", "stderr": str(e)}

def leb_run(cmd: str, base: str = "...", timeout: float = 60.0) -> Dict[str, Any]:
    """Executor used by tests and pilot. Intercepts 'patch_apply'."""
    if cmd.strip().startswith("patch_apply"):
        return _run_patch_apply_inline(cmd)
    try:
        rc = subprocess.run(cmd, shell=True).returncode
        return {"ok": True, "rc": rc, "stdout": "", "stderr": ""}
    except Exception as e:
        return {"ok": False, "rc": 1, "stdout": "", "stderr": str(e)}

# === API expected by tests (propose/drive...) ==================================

def propose_step(step: str, out_path: Optional[str] = None) -> str:
    if out_path:
        Path(out_path).write_text("{}", encoding="utf-8")
        return str(out_path)
    return ""

def _load_tracker(path: Optional[str]):
    if not path or yaml is None:
        return {}
    try:
        txt = Path(path).read_text(encoding="utf-8")
        data = yaml.safe_load(txt) or {}
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}

def _resolve_iters(tracker_path: Optional[str], explicit_iters: Optional[int]) -> int:
    if explicit_iters is not None:
        return max(0, int(explicit_iters))
    cfg = _load_tracker(tracker_path or os.environ.get("PROJECT_TRACKER"))
    ar = cfg.get("auto_revise") or {}
    if not bool(ar.get("enabled", False)):
        return 1
    n = int(ar.get("default_iters", 1))
    ui_max = ar.get("ui_soft_max", None)
    if ui_max is not None:
        try:
            n = min(n, int(ui_max))
        except Exception:
            pass
    return max(1, n)

def drive(step: str,
          tests: List[str] | str,
          flags: Optional[List[str]] = None,
          really_apply: bool = False,
          retries: Optional[int] = None,
          tracker_path: Optional[str] = None,
          out_dir: Optional[str] = None,
          iters: Optional[int] = None) -> int:
    if isinstance(tests, list):
        test_str = " ".join(tests)
    else:
        test_str = str(tests or "tests")
    flag_str = " ".join(flags or [])
    n = _resolve_iters(tracker_path, iters)
    base = Path(out_dir) if out_dir else None
    last_rc = 1
    for i in range(n):
        out_path = str((base / f"p{i+1}.json")) if base else None
        propose_step(step, out_path=out_path)
        cmd = "pytest"
        if flag_str:
            cmd += f" {flag_str}"
        if test_str:
            cmd += f" {test_str}"
        res = leb_run(cmd)
        last_rc = int(res.get("rc", 1))
        if last_rc == 0:
            apply_cmd = "patch_apply"
            apply_cmd += " --apply" if really_apply else " --dry-run"
            if out_path:
                apply_cmd += f" {out_path}"
            _ = leb_run(apply_cmd.strip())
            break
    return last_rc

def auto_revise_loops(step: str,
                      out_dir: Optional[str] = None,
                      tracker_path: Optional[str] = None,
                      iters: Optional[int] = None) -> int:
    n = _resolve_iters(tracker_path, iters)
    base = Path(out_dir) if out_dir else None
    did = 0
    for i in range(n):
        did += 1
        out_path = str((base / f"p{i+1}.json")) if base else None
        propose_step(step, out_path=out_path)
        res = leb_run("pytest -q")
        rc = int(res.get("rc", 1))
        if rc == 0:
            _ = leb_run(f"patch_apply --dry-run {out_path or ''}".strip())
            break
    return did

drive_auto_revise_loops = auto_revise_loops
_maybe_auto_revise = auto_revise_loops
_auto_revise = auto_revise_loops

def main():
    parser = build_parser()
    args, extra = parser.parse_known_args()
    tests = args.tests or "tests"
    pytest_flags = list(args.pytest_flags) + list(extra or [])
    rc = _run_pytest_subprocess(tests, pytest_flags)
    attempts = 0
    while rc != 0 and attempts < (args.retries or 0):
        attempts += 1
        rc = _run_pytest_subprocess(tests, pytest_flags)
    sys.exit(rc)

if __name__ == "__main__":
    main()
