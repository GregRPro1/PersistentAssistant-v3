
APPLY
-----
pwsh .\apply_packs_only.ps1 -ZipPath "$env:USERPROFILE\Downloads\PAL20251012A_fix2.zip"

WHAT'S NEW
----------
- Robust server wrapper: auto-detects repo root; tries current/server.py, releases/current/server.py, root/server.py.
- Smoke test: retries + localhost fallback + optional -HealthUrl.
- PAL process snapshot tool: captures processes/listeners/tunnel list and tries to git-commit logs.
- Fallback simple HTTP server launcher for port 8787.
