Daily dev loop (fast)

Bring up agent (fallback is fine for MVP):

python tools\py\pa_agent_bringup.py --host 127.0.0.1 --port 8782 --timeout 30
powershell -NoProfile -ExecutionPolicy Bypass -File tools\auto_health.ps1
python tools\py\mvp_smoke.py


Snapshot + pack (keeps us aligned):

python tools\py\pa_std_summary.py --level standard
python tools\py\pack\enrich_pack.py
python tools\py\pack\verify_pack.py --include-meta --check-insights


CI gate:

python tools\py\ci\ci_check.py