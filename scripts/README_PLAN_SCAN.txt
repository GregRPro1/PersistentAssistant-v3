# PAL Plan Scan Tool
This installs `scripts/tools/scan_and_bundle_plans.py` which scans the repo for plan/tracker files
and creates a single bundle zip you can share back for consolidation.

## Usage (PowerShell)
```powershell
# From repo root
python .\scripts\tools\scan_and_bundle_plans.py --include-state
# Optional: custom output path
python .\scripts\tools\scan_and_bundle_plans.py --include-state --out "$env:USERPROFILE\Desktop\PAL_plan_bundle.zip"
# Optional: add extra globs (relative to repo root)
python .\scripts\tools\scan_and_bundle_plans.py --extra "_context\**\*.md" --extra "plans\**\*.yaml"
```

Outputs:
- `reports\plan_scan_manifest.json` (summary list + hashes)
- `PAL_plan_bundle_<timestamp>.zip` (at repo root by default)
