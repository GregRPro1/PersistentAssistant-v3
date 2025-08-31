# tools/py/agentic/propose_for_step.py
from __future__ import annotations
# --- PA_ROOT_IMPORT ---
import sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[3]  # .../tools/py/agentic -> repo root
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
# --- /PA_ROOT_IMPORT ---

import argparse, json, hashlib
from datetime import datetime, timezone
from pathlib import Path

from tools.py.agentic.patch_utils import sha256_hex, ensure_dir  # uses file-path hashing

TARGET_FILE = Path("docs/USER_GUIDE.md")  # safe target in your tree

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def sha256_of_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def build_proposal(step_id: str) -> dict:
    abs_target = (ROOT / TARGET_FILE).resolve()
    if abs_target.exists():
        # ✅ hash the FILE via your helper (expects a path)
        before = sha256_hex(abs_target)
    else:
        # File missing: guard against "empty"
        before = sha256_of_text("")  # e3b0c442... (sha256 of empty string)

    content = (
        f"\n\n> [plan] placeholder for step {step_id} (agentic bootstrap) @ "
        f"{int(datetime.now().timestamp())}\n"
    )

    return {
        # keep DEV-DRY-RUN while we’re still in dry-run everywhere
        "feature_id": "DEV-DRY-RUN",
        "version": 1,
        "author": "propose_for_step",
        "created": now_iso(),
        "actions": [
            {
                "path": str(TARGET_FILE).replace("\\", "/"),
                "mode": "append",
                "before_sha": before,  # <-- REQUIRED for patch_apply to accept
                "content": content,
            }
        ],
    }

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--id", required=True, help="plan step id (e.g. 10.3)")
    p.add_argument("--out", required=True, help="output proposal path (relative OK)")
    p.add_argument("--force", action="store_true", help="overwrite if exists")
    args = p.parse_args()

    out_path = (ROOT / args.out).resolve()
    if out_path.exists() and not args.force:
        print(str(out_path))
        return 0

    proposal = build_proposal(args.id)
    ensure_dir(out_path.parent)
    out_path.write_text(json.dumps(proposal, indent=2), encoding="utf-8")
    print(str(out_path))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
