# Tool Catalog

- **CI Gate** () — ``  
  usage: `python tools/py/ci/ci_check.py`  
  reply-lint → guard test → std summary → build catalog → enrich → verify
- **MVP Smoke** () — ``  
  usage: `python tools/py/mvp_smoke.py`  
  Hit core agent endpoints and report HTTP status; nonzero on failure.
- **Pack Enrich** () — ``  
  usage: `python tools/py/pack/enrich_pack.py`  
  Inject plan snapshot, tool catalog, and reporters into a pack.
- **Pack Verify** () — ``  
  usage: `python tools/py/pack/verify_pack.py --include-meta --check-insights`  
  Verify pack contains plan/catalog/reporters; auto-picks latest.
- **Reply Lint (selected)** () — ``  
  usage: `python tools/py/ci/reply_lint_selected.py`  
  Windows-safe linter for heredocs/here-strings in curated files.
- **Std Summary** () — ``  
  usage: `python tools/py/pa_std_summary.py --level standard`  
  orchestrator
- **/agent/_sig** (endpoint) — `/agent/_sig`  
  usage: `GET /agent/_sig`  
  Flask route (GET,HEAD,OPTIONS)
- **/agent/ac** (endpoint) — `/agent/ac`  
  usage: `GET /agent/ac`  
  Flask route (GET,HEAD,OPTIONS)
- **/agent/approvals_count** (endpoint) — `/agent/approvals_count`  
  usage: `GET /agent/approvals_count`  
  Flask route (GET,HEAD,OPTIONS)
- **/agent/next2** (endpoint) — `/agent/next2`  
  usage: `GET /agent/next2`  
  Flask route (GET,HEAD,OPTIONS,POST)
- **/agent/plan** (endpoint) — `/agent/plan`  
  usage: `GET /agent/plan`  
  Flask route (GET,HEAD,OPTIONS)
- **/agent/recent** (endpoint) — `/agent/recent`  
  usage: `GET /agent/recent`  
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
