Persistent Assistant — Quick Ops Notes

Run all commands from the repo root with your virtualenv active:
(.venv) PS C:\_Repos\PersistentAssistant>

1) Check web/agent endpoints
python tools\py\pa_agent_bringup.py --host 127.0.0.1 --port 8782 --timeout 30
powershell -NoProfile -ExecutionPolicy Bypass -File tools\auto_health.ps1

2) Open the Agent UI
start http://127.0.0.1:8782/pwa/agent

3) Snapshot the project (full diagnostic pack)
python tools\py\pa_project_snapshot.py

4) “Standard Snapshot & Pack” (recommended 3-step)
python tools\py\pa_std_summary.py --level standard
python tools\py\pack\enrich_pack.py
python tools\py\pack\verify_pack.py --include-meta --check-insights


Produces/validates:

project\structure\file_manifest.yaml

project\structure\project_structure_snapshot_index.md

data\insights\*

plan_snapshot.yaml

tools\tool_catalog.{json,yaml,md}

Pack ZIP in tmp\feedback\pack_project_snapshot_*.zip

5) Show next project step
python tools\show_next_step.py

6) Watchdog bootstrap (agent heartbeat + alerts)
python tools\py\pa_bootstrap.py --host 127.0.0.1 --port 8782 --minutes 2 --email grapson_pro1@outlook.com --phone +447894798589

7) Plan updates
python tools\py\plan_step_add.py --id 6.4.c --title "Add Agent Watchdog + Alerting" --status planned --desc "Install watchdog, schedule every 2 min, YAML-configured notifications; enter backoff if flapping."

8) Tool catalog (discoverable tools registry)

Build/refresh the catalog:

python tools\py\registry\build_tool_catalog.py --host 127.0.0.1 --port 8782


Add a tool to the catalog:

python tools\py\registry\add_tool.py --kind endpoint --ref /agent/plan --title "Agent Plan API" --description "Returns structured plan state (JSON)."

9) Lightweight file summaries (reporters)

Ensure the manifest exists:

python tools\file_manifest.py


Generate the structure index:

python tools\py\inventory\report_index.py


Extract headers and MD headings:

python tools\py\inventory\report_headers.py

10) Local CI gate (same pipeline as Actions)
python tools\py\ci\ci_check.py


This runs: reply-lint → tool-dup guard test → standard summary → build catalog → enrich pack → verify pack.

Tips

Catch bad escapes early:

$env:PYTHONWARNINGS='error::SyntaxWarning'
python -X dev tools\py\pa_std_summary.py --level standard


Latest pack lives in:

tmp\feedback\pack_project_snapshot_*.zip


If you change tools, re-build the catalog before enriching packs:

python tools\py\registry\build_tool_catalog.py --host 127.0.0.1 --port 8782
python tools\py\pack\enrich_pack.py
python tools\py\pack\verify_pack.py --include-meta --check-insights





------------------------------------------------------------------------------------

Notes

To check web sites working

python tools\py\pa_agent_bringup.py --host 127.0.0.1 --port 8782 --timeout 30
powershell -NoProfile -ExecutionPolicy Bypass -File tools\auto_health.ps1

To snapshot the project
python tools\py\pa_project_snapshot.py


To show next project step
python tools/show_next_step.py


To show the agent 
start http://127.0.0.1:8782/pwa/agent

To bootstrap the watchdog
python tools\py\pa_bootstrap.py --host 127.0.0.1 --port 8782 --minutes 2 --email grapson_pro1@outlook.com --phone +447894798589

To add to the plan
python tools\py\plan_step_add.py --id 6.4.c --title "Add Agent Watchdog + Alerting" --status planned --desc "Install watchdog, schedule every 2 min, YAML-configured notifications; enter backoff if flapping."

To build tool_cataglog
python tools\py\registry\build_tool_catalog.py --host 127.0.0.1 --port 8782

To add tool to register
python tools\py\registry\add_tool.py --kind endpoint --ref /agent/plan --title "Agent Plan API" --description "Returns structured plan state (JSON)."


To create summary
# 1) Ensure manifest exists (your existing tool)
python tools\file_manifest.py

# 2) Generate index MD (read-only; fast)
python tools\py\inventory\report_index.py

# 3) Extract headers + MD headings (read-only; fast)
python tools\py\inventory\report_headers.py
