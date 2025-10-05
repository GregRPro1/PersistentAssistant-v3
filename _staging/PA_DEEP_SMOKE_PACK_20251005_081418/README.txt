PA_DEEP_SMOKE_PACK
===================

WHAT THIS PACK DOES
- Installs tools\ps1\deep_smoke.ps1 (diagnostics + optional recovery).
- Does NOT modify Python code. Safe to apply multiple times.

HOW TO APPLY
1) Unzip anywhere under your repo's _staging, then run:
   pwsh -NoProfile -ExecutionPolicy Bypass -File <unzipped>\scripts\apply_pack.ps1

   (If you used our previous convention: expand under _staging\PA_DEEP_SMOKE_PACK_* and run its scripts\apply_pack.ps1)

2) Run Deep Smoke (analysis only):
   pwsh tools\ps1\deep_smoke.ps1

   Or with recovery attempts (stop/start watchdog, restart tunnel):
   pwsh tools\ps1\deep_smoke.ps1 -Restart

OUTPUTS
- tmp\logs\deep_smoke_report.json
- tmp\logs\double_prefix_report.json
- tmp\logs\module_paths.json
- reports\ops\tunnel_url.txt
- reports\ops\phone_watchdog_url.txt
- tmp\logs\deep_smoke_dump_YYYYMMDD_HHMMSS.zip
