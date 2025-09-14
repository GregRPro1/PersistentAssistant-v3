# Tool Catalog

- **Agent Bringup** () — ``  
  usage: `python tools/py/pa_agent_bringup.py --host 127.0.0.1 --port 8783 --timeout 20 --force-kill`  
  Probe/launch sidecar; now with --force-kill to free port.
- **Daily Dev Loop** () — ``  
  usage: `python tools/py/daily/daily_dev_loop.py --mode brief`  
  reply-lint → smoke → summary → catalog → enrich → verify; writes data/status/daily_status.json
- **Port Kill** () — ``  
  usage: `python tools/py/net/port_kill.py --port 8783`  
  Kill Windows listeners on a port (netstat/taskkill).
- **/agent/_sig** (endpoint) — `/agent/_sig`  
  usage: `GET /agent/_sig`  
  Flask route (GET,HEAD,OPTIONS)
- **/agent/ac** (endpoint) — `/agent/ac`  
  usage: `GET /agent/ac`  
  Flask route (GET,HEAD,OPTIONS)
- **/agent/apply** (endpoint) — `/agent/apply`  
  usage: `GET /agent/apply`  
  Flask route (OPTIONS,POST)
- **/agent/approvals_count** (endpoint) — `/agent/approvals_count`  
  usage: `GET /agent/approvals_count`  
  Flask route (GET,HEAD,OPTIONS)
- **/agent/approvals_count** (endpoint) — `/agent/approvals_count`  
  usage: `GET /agent/approvals_count`  
  Flask route (GET,HEAD,OPTIONS)
- **/agent/approvals_count** (endpoint) — `/agent/approvals_count`  
  usage: `GET /agent/approvals_count`  
  Flask route (GET,HEAD,OPTIONS)
- **/agent/compose** (endpoint) — `/agent/compose`  
  usage: `GET /agent/compose`  
  Flask route (GET,HEAD,OPTIONS,POST)
- **/agent/leb/ping** (endpoint) — `/agent/leb/ping`  
  usage: `GET /agent/leb/ping`  
  Flask route (GET,HEAD,OPTIONS)
- **/agent/leb/run** (endpoint) — `/agent/leb/run`  
  usage: `GET /agent/leb/run`  
  Flask route (OPTIONS,POST)
- **/agent/next2** (endpoint) — `/agent/next2`  
  usage: `GET /agent/next2`  
  Flask route (GET,HEAD,OPTIONS)
- **/agent/next2** (endpoint) — `/agent/next2`  
  usage: `GET /agent/next2`  
  Flask route (GET,HEAD,OPTIONS)
- **/agent/plan** (endpoint) — `/agent/plan`  
  usage: `GET /agent/plan`  
  Flask route (GET,HEAD,OPTIONS)
- **/agent/project/new** (endpoint) — `/agent/project/new`  
  usage: `GET /agent/project/new`  
  Flask route (OPTIONS,POST)
- **/agent/propose** (endpoint) — `/agent/propose`  
  usage: `GET /agent/propose`  
  Flask route (GET,HEAD,OPTIONS)
- **/agent/propose** (endpoint) — `/agent/propose`  
  usage: `GET /agent/propose`  
  Flask route (OPTIONS,POST)
- **/agent/recent** (endpoint) — `/agent/recent`  
  usage: `GET /agent/recent`  
  Flask route (GET,HEAD,OPTIONS)
- **/agent/recent** (endpoint) — `/agent/recent`  
  usage: `GET /agent/recent`  
  Flask route (GET,HEAD,OPTIONS)
- **/agent/recent** (endpoint) — `/agent/recent`  
  usage: `GET /agent/recent`  
  Flask route (GET,HEAD,OPTIONS)
- **/agent/settings** (endpoint) — `/agent/settings`  
  usage: `GET /agent/settings`  
  Flask route (GET,HEAD,OPTIONS)
- **/agent/settings** (endpoint) — `/agent/settings`  
  usage: `GET /agent/settings`  
  Flask route (OPTIONS,POST)
- **/agent/settings/get** (endpoint) — `/agent/settings/get`  
  usage: `GET /agent/settings/get`  
  Flask route (GET,HEAD,OPTIONS)
- **/agent/settings/set** (endpoint) — `/agent/settings/set`  
  usage: `GET /agent/settings/set`  
  Flask route (OPTIONS,POST)
- **/agent/summary** (endpoint) — `/agent/summary`  
  usage: `GET /agent/summary`  
  Flask route (GET,HEAD,OPTIONS)
- **/agent/summary** (endpoint) — `/agent/summary`  
  usage: `GET /agent/summary`  
  Flask route (GET,HEAD,OPTIONS)
- **/agent/summary** (endpoint) — `/agent/summary`  
  usage: `GET /agent/summary`  
  Flask route (GET,HEAD,OPTIONS)
- **/agent/ui** (endpoint) — `/agent/ui`  
  usage: `GET /agent/ui`  
  Flask route (GET,HEAD,OPTIONS)
- **/agent/worker_status** (endpoint) — `/agent/worker_status`  
  usage: `GET /agent/worker_status`  
  Flask route (GET,HEAD,OPTIONS)
- **/agent/ws** (endpoint) — `/agent/ws`  
  usage: `GET /agent/ws`  
  Flask route (GET,HEAD,OPTIONS)
- **/agent_routes** (endpoint) — `/agent_routes`  
  usage: `GET /agent_routes`  
  Flask route (GET,HEAD,OPTIONS)
- **/health** (endpoint) — `/health`  
  usage: `GET /health`  
  Flask route (GET,HEAD,OPTIONS)
- **/pwa/agent** (endpoint) — `/pwa/agent`  
  usage: `GET /pwa/agent`  
  Flask route (GET,HEAD,OPTIONS)
- **Daily Status API** (endpoint) — `/agent/daily_status`  
  usage: `GET /agent/daily_status`  
  Returns data/status/daily_status.json (ok,data|error).
