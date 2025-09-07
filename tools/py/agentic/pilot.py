from __future__ import annotations
import json
from pathlib import Path
from typing import List, Optional, Dict, Any
from . import ai_link
from . import drive_step as ds
from .status import write_status

def run_once(step: str,
             tests: List[str] | str,
             flags: Optional[List[str]] = None,
             out_dir: Optional[str] = None,
             iters: int = 2,
             really_apply: bool = False,
             tracker_path: Optional[str] = None,
             status_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Semi-automatic loop: propose -> test (leb_run) -> repeat up to iters.
    - Writes status JSON each attempt (phase: propose, test).
    - On failure, next proposal receives context['last_error'] with rc/stdout/stderr.
    Returns: { ok: bool, rc: int, attempts: int, last_proposal: str }
    """
    base = Path(out_dir) if out_dir else Path("tmp/agentic/proposals")
    base.mkdir(parents=True, exist_ok=True)
    last = None
    rc = 1
    attempts = 0
    last_error: Dict[str, Any] | None = None

    # normalize tests/flags
    if isinstance(tests, list):
        test_str = " ".join(tests)
    else:
        test_str = str(tests or "tests")
    flag_str = " ".join(flags or ["-q"])

    for i in range(max(1, iters)):
        attempts += 1
        out_path = base / f"p{i+1}.json"

        # --- propose ---
        context: Dict[str, Any] = {"attempt": i + 1}
        if last_error is not None:
            context["last_error"] = last_error
        last = ai_link.compose_proposal(step=step, context=context, out_path=str(out_path))
        write_status({
            "phase": "propose",
            "step": step,
            "attempt": attempts,
            "total": iters,
            "last_proposal": last
        }, status_path)

        # --- test via leb_run ---
        cmd = "pytest"
        if flag_str:
            cmd += f" {flag_str}"
        if test_str:
            cmd += f" {test_str}"
        res = ds.leb_run(cmd)
        rc = int(res.get("rc", 1))
        last_error = {
            "rc": rc,
            "stdout": res.get("stdout", ""),
            "stderr": res.get("stderr", ""),
        }
        write_status({
            "phase": "test",
            "step": step,
            "attempt": attempts,
            "total": iters,
            "last_proposal": last,
            "rc": rc,
            "ok": (rc == 0)
        }, status_path)

        if rc == 0:
            # simulate apply action (dry-run unless really_apply)
            apply_cmd = "patch_apply"
            apply_cmd += " --apply" if really_apply else " --dry-run"
            apply_cmd += f" {last or ''}"
            _ = ds.leb_run(apply_cmd.strip())
            break

    return {"ok": rc == 0, "rc": rc, "attempts": attempts, "last_proposal": last}
