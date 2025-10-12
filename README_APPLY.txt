# PAL — Robust Tunnel & Diagnostics Pack
Apply:
  pwsh .\scripts\apply_pack.ps1 -ZipPath "$env:USERPROFILE\Downloads\PAL_Robust_Tunnel_And_Diagnostics_Pack.zip"
Bring up (watchdog + clean state):
  pwsh .\pal\scripts\ps\pal_reset_watchdog_env.ps1
Create quick tunnel (auto-discover/install cloudflared; logs -> tmp/logs):
  pwsh .\pal\scripts\ps\run_quick_tunnel.ps1 -Port 8787
Smoke test:
  pwsh .\pal\scripts\ps\smoke_cloudflared.ps1
Commit diagnostics:
  pwsh .\pal\scripts\ps\commit_logs.ps1
Logs:
  .\tmp\logs\watchdog.log, cloudflared.out.log, cloudflared.err.log
Ops snapshot:
  .\reports\ops\ops_status.json
