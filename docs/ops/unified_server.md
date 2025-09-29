# Unified Server (PA-350)
A non-invasive harness that **auto-mounts existing server modules** into one port.

- Config: `config/unified_server.yaml` (host, port, token env, candidate modules)
- Run: `pwsh tools\ps1\run_unified_server.ps1`
- Report: `reports/ops/unified_server_report.json` lists what mounted and why

## Auth
If env var named by `token_env` (default `PA_WEB_TOKEN`) is set, remote calls must send:
```
Authorization: Bearer <token>
```
Localhost requests are allowed without token.