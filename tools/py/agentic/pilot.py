from __future__ import annotations
import json
from pathlib import Path
from typing import List, Optional, Dict, Any
from . import ai_link
from .proposal_types import proposal_minimal_dict
from . import drive_step as ds

def run_once(step: str,
             tests: List[str] | str,
             flags: Optional[List[str]] = None,
             out_dir: Optional[str] = None,
             iters: int = 2,
             really_apply: bool = False,
             tracker_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Semi-automatic loop: propose -> test (via drive_step.drive) -> repeat up to iters.
    Returns a dict with ok(bool), rc(int), attempts(int), last_proposal(str|None).
    """
    base = Path(out_dir) if out_dir else Path("tmp/agentic/proposals")
    base.mkdir(parents=True, exist_ok=True)
    last = None
    rc = 1
    attempts = 0
    for i in range(max(1, iters)):
        attempts += 1
        out_path = base / f"p{i+1}.json"
        # Ask AI (or stub) for a proposal artifact
        last = ai_link.compose_proposal(step=step, context={"attempt": i+1}, out_path=str(out_path))
        # Run tests through drive() which uses leb_run under the hood
        rc = ds.drive(step=step, tests=tests, flags=flags or ["-q"], really_apply=really_apply,
                      tracker_path=tracker_path, out_dir=str(base), iters=1)
        if rc == 0:
            break
    return {"ok": rc == 0, "rc": rc, "attempts": attempts, "last_proposal": last}
