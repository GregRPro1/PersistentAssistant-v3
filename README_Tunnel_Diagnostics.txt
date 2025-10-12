# Tunnel Robust Diagnostics Patch

New capabilities:
- `palctl tunnel-quick --verbose --stdout-timeout 45` echoes cloudflared output and writes `reports/smoke/PAL-TUNNEL-RUN.json`.
- `palctl tunnel-diagnose` runs origin checks, discovery, tunnel, remote /healthz and writes `reports/smoke/PAL-TUNNEL-DIAG.json`.
- `palctl tunnel-verify` fetches current tunnel URL and verifies `/healthz`.
- Strong warnings if origin port is not listening.

Examples:
```
python .\current\server.py  # ensure origin is up
python -m pal.cli tunnel-quick --port 8787 --verbose
python -m pal.cli tunnel-diagnose --port 8787 --health http://127.0.0.1:8787/healthz --verbose
python -m pal.cli tunnel-verify
```