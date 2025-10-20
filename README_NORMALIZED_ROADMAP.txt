Install this pack to write a normalized roadmap and run a code compatibility scan.

Apply:
  python .\scripts\apply_pack.py -ZipPath "$env:USERPROFILE\Downloads\PAL20251019E_normalized_roadmap_and_compat_pack.zip"

Run compat scan (repo root):
  python .\scripts\tools\scan_plan_schema_compat.py > reports\plan_schema_scan.json
  # exit code 1 if old-plan assumptions are present

The normalized roadmap is at:
  plans\roadmap\consolidated_roadmap.normalized.yaml
