# Tool Catalog

- **Agent Bringup** () — ``  
  usage: `python tools/py/pa_agent_bringup.py --host 127.0.0.1 --port 8783 --timeout 20 --force-kill`  
  Probe/launch sidecar; now with --force-kill to free port.
- **Daily Dev Loop** () — ``  
  usage: `python tools/py/daily/daily_dev_loop.py --mode brief`  
  reply-lint → smoke → summary → catalog → enrich → verify; writes data/status/daily_status.json
- **Daily Status API** () — ``  
  usage: ``  
  Returns data/status/daily_status.json (ok,data|error).
- **Port Kill** () — ``  
  usage: `python tools/py/net/port_kill.py --port 8783`  
  Kill Windows listeners on a port (netstat/taskkill).
