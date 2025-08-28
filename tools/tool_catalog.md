# Tool Catalog

- **Audit Inventory (legacy)** () — ``  
  usage: `python tools/audit_inventory.py`  
  [DEPRECATE] Thin Python-only inventory (func/class names, feature_id tags). Superseded by Deep Inventory.
- **Deep Inventory** () — ``  
  usage: `python tools/deep_inventory.py`  
  Rich Python AST scan: imports, funcs/classes, call-exprs, call-graph DOT, docstring gaps, duplication reports; writes data/insights/*.
- **Dev Summary** () — ``  
  usage: `python tools/make_summary.py`  
  Refresh deep inventory, show plan status, tail logs, write last_summary.txt (clipboard if available).
- **File Manifest** () — ``  
  usage: `python tools/file_manifest.py`  
  Canonical repo manifest across code/docs; SHA256, size, mtime, LOC, funcs; writes project/structure/file_manifest.yaml.
- **Find Callers** () — ``  
  usage: `python tools/find_callers.py <symbol>`  
  List callers of a symbol using deep_calls.yaml from Deep Inventory.
- **Find File by Name** () — ``  
  usage: `python tools/find_file.py <name>`  
  Locate file by basename using deep_inventory.yaml, else glob fallback.
- **Manifest Query** () — ``  
  usage: `python tools/manifest_query.py --path <glob> --verify --emit-header`  
  Query/verify file_manifest.yaml; optional Expected-SHA256 header emit.
- **PA Bootstrap** () — ``  
  usage: `python tools/py/pa_bootstrap.py --host 127.0.0.1 --port 8782 --minutes 2`  
  Create YAML, install Scheduled Task, start agent, print status.
- **Pack Enrich** () — ``  
  usage: `python tools/py/pack/enrich_pack.py`  
  Inject plan snapshot, tool catalog, and reporters into a pack.
- **Pack Verify** () — ``  
  usage: `python tools/py/pack/verify_pack.py --include-meta`  
  Verify pack contains plan/catalog/reporters; auto-picks latest.
- **Project Snapshot Pack** () — ``  
  usage: `python tools/py/pa_project_snapshot.py`  
  One-shot snapshot: env, server compile, wrapper import, auto_health (if present), log tails, repo manifest, and pack zip.
- **Reply Lint** () — ``  
  usage: `python tools/py/lint/reply_lint.py --path <file>`  
  Scan text for heredocs/here-strings and banned constructs; fail fast.
- **Report Headers** () — ``  
  usage: `python tools/py/inventory/report_headers.py`  
  Extract header comments (.py/.yml/.yaml) and top MD headings; write insights YAMLs.
- **Report Index** () — ``  
  usage: `python tools/py/inventory/report_index.py`  
  Emit project_structure_snapshot_index.md from file_manifest.yaml.
- **Standard Summary Orchestrator** () — ``  
  usage: `python tools/py/pa_std_summary.py --level standard`  
  One-shot: manifest -> reporters -> (optional) deep inventory -> snapshot pack; prints PACK/STATUS.
- **Structure Snapshot (legacy)** () — ``  
  usage: `python tools/structure_sync.py`  
  [DEPRECATE] Light structure pass (headers, md headings, python sigs). Fold into deep_inventory extras + report_index.
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
- **Agent Plan API** (endpoint) — `/agent/plan`  
  usage: `GET /agent/plan`  
  Returns structured plan state (JSON).
- **Simple Patcher** (py) — `tools/apply_simple_patches.py`  
  usage: `python tools/apply_simple_patches.py --patch tmp\\llm\\patch.json`  
  Apply literal, JSON-defined text patches with backups (all/nth support).
