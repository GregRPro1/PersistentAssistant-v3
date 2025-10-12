
# PAL Blocking/UI Watchdog + Tunnel Robustness Patch

## Apply
```
cd C:\_Repos\PersistentAssistant
pwsh .\scripts\apply_pack.ps1 -ZipPath "$env:USERPROFILE\Downloads\PAL_Blocking_UI_Watchdog_Tunnel_Patch.zip"
```

## What changed
- **Blocking banners** on long-running processes (dev web, watchdog UI).
- **Watchdog UI** (`watchdog-ui`) shows live lights for web/tunnel/phone/watcher.
- **Tunnel commands** print clear expectations and write detailed JSON + logs.

## Typical workflow
### Terminal A (BLOCKING)
```
python .\current\server.py
```
Expected: banner printed, periodic /healthz logs.

### Terminal B (BLOCKING dashboard)
```
python -m pal.cli watchdog-ui
```
Expected: live table; Ctrl+C exits (child processes keep running).

### Terminal C (RETURNS)
```
# Optional: set known cloudflared path
$env:CLOUDFLARED_EXE="C:\Program Files\cloudflared\cloudflared.exe"

# Diagnose end-to-end (writes reports/smoke/PAL-TUNNEL-DIAG.json)
python -m pal.cli tunnel-diagnose --port 8787 --health http://127.0.0.1:8787/healthz --verbose

# Start tunnel (writes reports/ops/tunnel_url.txt or a failure JSON)
python -m pal.cli tunnel-quick --port 8787 --verbose

# Verify over public URL then refresh tracker status
python -m pal.cli tunnel-verify
python -m pal.cli ops-snapshot -c pal/config/pal.yaml
python -m pal.cli status
```
Logs: `tmp/logs/cloudflared.out.log`, `tmp/logs/cloudflared.err.log`
Artifacts: `reports/smoke/PAL-TUNNEL-RUN.json`, `reports/smoke/PAL-TUNNEL-DIAG.json`
