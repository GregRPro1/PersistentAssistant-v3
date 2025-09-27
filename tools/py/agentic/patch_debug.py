# tools/py/agentic/patch_debug.py
from __future__ import annotations
# --- PA_ROOT_IMPORT ---
import sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
# --- /PA_ROOT_IMPORT ---

import argparse, json
from pathlib import Path
from tools.py.agentic.patch_utils import sha256_hex

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--proposal", required=True)
    args = p.parse_args()

    prop_path = (ROOT / args.proposal).resolve() if not Path(args.proposal).is_absolute() else Path(args.proposal)
    data = json.loads(prop_path.read_text(encoding="utf-8"))
    actions = data.get("actions") or []
    out = {"proposal": str(prop_path), "actions": []}
    for a in actions:
        pth = a.get("path")
        mode = a.get("mode")
        before = (a.get("before_sha") or "").lower()
        abs_p = (ROOT / pth).resolve()
        exists = abs_p.exists()
        have = sha256_hex(abs_p) if exists else None
        out["actions"].append({
            "path": pth,
            "abs": str(abs_p),
            "mode": mode,
            "exists": exists,
            "before_sha": before or None,
            "have_sha": have,
            "match": (before == (have or "").lower()) if before and have else None
        })
    print(json.dumps(out, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
