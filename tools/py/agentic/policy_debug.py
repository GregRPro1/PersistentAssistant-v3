from __future__ import annotations
import argparse, json, sys
from pathlib import Path

from .policy_utils import load_policy, match_globs, ROOT

def main() -> int:
    ap = argparse.ArgumentParser(description="Show effective runner policy and matching proof.")
    ap.add_argument("--policy", help="Optional explicit path to runner_policy.yaml")
    ap.add_argument("--check-path", help="Repo-relative path to probe against allow/deny (e.g., docs/USER_GUIDE.md)")
    ap.add_argument("--json", action="store_true", help="Emit JSON only (no extra text)")
    args = ap.parse_args()

    eff, diag = load_policy(args.policy)
    out = {
        "policy_diagnostics": diag,
        "note": "Set PA_POLICY_PATH env var to force a specific policy file if needed.",
    }

    if args.check_path:
        rel = args.check_path.replace("\\", "/")
        out["path_check"] = match_globs(rel, eff["allow_globs"], eff["deny_globs"])

    if not args.json:
        print(json.dumps(out, indent=2))
    else:
        print(json.dumps(out))
    return 0

if __name__ == "__main__":
    sys.exit(main())
