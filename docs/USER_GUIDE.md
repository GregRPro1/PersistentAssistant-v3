# Persistent Assistant — User Guide

This guide shows how to run the system, use the Plan UI, start agentic work on a step, approve patches, and keep the project under control.

## 1) Setup & bring-up

Run from repo root with your venv active:
```powershell
# Ensure port is free (change port if needed)
python tools\py\net\port_kill.py --port 8783

# Launch sidecar wrapper (writes logs under tmp\logs\)
python tools\py\pa_agent_bringup.py --host 127.0.0.1 --port 8783 --timeout 20 --force-kill

# Open the UI
start http://127.0.0.1:8783/pwa/agent



> [plan] placeholder for step 10.3 (agentic bootstrap) @ 1756668966


> [plan] placeholder for step 10.4 (agentic bootstrap) @ 1756936392


> [plan] placeholder for step 10.4 (agentic bootstrap) @ 1757264744
