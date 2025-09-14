# PersistentAssistant Change Protocol
**Version:** 1.1 • **Date:** 2025‑09‑14  
**Scope:** Disciplined, repeatable flow for diagnosing, changing, and verifying the PersistentAssistant codebase and UI.

---

## Why this exists
We’ve had regressions caused by ad‑hoc edits, terminal pasting mix‑ups, and cache confusion. This protocol turns every change into a small, auditable experiment: **diagnose → request files → apply → smoke test → verify UI → package evidence**.

---

## Golden Rules (Do These Every Time)
1. **Always start with diagnostics.** Never edit until you’ve reproduced the issue and captured proof (routes, served assets, logs).
2. **Request files, don’t guess.** If a change is needed, **ask for the exact file(s)** via the support‑bundle process and propose a **surgical patch** with before/after anchors.
3. **One change per patch.** Keep patches minimal, idempotent, and reversible. Include compile/check commands.
4. **Smoke tests after every change.** Run API health, route inventory, and the smallest repro you can, then UI checks.
5. **Favor served‑asset verification.** Compare **served** `settings_ext.js` vs **on‑disk** to avoid cache illusions. Bust cache with `?v=` bumps.
6. **Package artifacts.** Produce a support bundle zip with changed files, server logs, and HTTP captures.
7. **No background promises.** Do work now, show outputs now.
8. **Terminal vs. file discipline.** PowerShell can interpret pasted JS/PS/JSON. When in doubt, **write a patch script** or provide exact `Set-Content` commands.
9. **Idempotency.** Patches must be safe to apply multiple times and leave the system in a good state.

---

## Daily Bring‑Up (Baseline Health)
Run from repo root with your venv active:

```pwsh
# Health + bringup
python tools\py\pa_agent_bringup.py --host 127.0.0.1 --port 8782 --timeout 30
# Agent/Phone auto‑health sweep
powershell -NoProfile -ExecutionPolicy Bypass -File tools\auto_health.ps1
```

Output should show `OK: /health 200` and a clean routes table. Investigate any errors before proceeding.

---

## Open the Agent UI
```pwsh
start http://127.0.0.1:8782/pwa/agent
```

---

## Standard Snapshot & Pack (Recommended 3‑Step)
Creates a project snapshot + insights + verified pack.

```pwsh
python tools\py\pa_std_summary.py --level standard
python tools\py\pack\enrich_pack.py
python tools\py\pack\verify_pack.py --include-meta --check-insights
```

**Produces / validates**

- `project\structure\file_manifest.yaml`  
- `project\structure\project_structure_snapshot_index.md`  
- `data\insights\*` (headers, imports, deep inventory, etc.)  
- `plan_snapshot.yaml`  
- `tools\tool_catalog.{json,yaml,md}` (if built)  
- Pack ZIP in `tmp\feedback\pack_project_snapshot_*.zip`

---

## “Quick Ops Notes” (Ready‑to‑Run)
From: `(.venv) PS C:\_Repos\PersistentAssistant>`

### 1) Check web/agent endpoints
```pwsh
python tools\py\pa_agent_bringup.py --host 127.0.0.1 --port 8782 --timeout 30
powershell -NoProfile -ExecutionPolicy Bypass -File tools\auto_health.ps1
```

### 2) Open the Agent UI
```pwsh
start http://127.0.0.1:8782/pwa/agent
```

### 3) Snapshot the project (full diagnostic pack)
```pwsh
python tools\py\pa_project_snapshot.py
```

### 4) Standard Snapshot & Pack (3‑step)
```pwsh
python tools\py\pa_std_summary.py --level standard
python tools\py\pack\enrich_pack.py
python tools\py\pack\verify_pack.py --include-meta --check-insights
```

### 5) Show next project step
```pwsh
python tools\show_next_step.py
```

### 6) Watchdog bootstrap (agent heartbeat + alerts)
```pwsh
python tools\py\pa_bootstrap.py --host 127.0.0.1 --port 8782 --minutes 2 --email grapson_pro1@outlook.com --phone +447894798589
```

### 7) Plan updates
```pwsh
python tools\py\plan_step_add.py --id 6.4.c --title "Add Agent Watchdog + Alerting" --status planned --desc "Install watchdog, schedule every 2 min, YAML-configured notifications; enter backoff if flapping."
```

### 8) Tool catalog (discoverable tools registry)
**Build/refresh:**
```pwsh
python tools\py\registry\build_tool_catalog.py --host 127.0.0.1 --port 8782
```

**Add a tool to the catalog:**
```pwsh
python tools\py\registry\add_tool.py --kind endpoint --ref /agent/plan --title "Agent Plan API" --description "Returns structured plan state (JSON)."
```

### 9) Lightweight file summaries (reporters)
```pwsh
# Ensure manifest exists
python tools\file_manifest.py

# Generate structure index
python tools\py\inventory\report_index.py

# Extract headers and MD headings
python tools\py\inventory\report_headers.py
```

### 10) Local CI gate (same pipeline as Actions)
```pwsh
python tools\py\ci\ci_check.py
```
Runs: reply‑lint → tool‑dup guard test → standard summary → build catalog → enrich pack → verify pack.

---

## Tips & Guardrails
- **Catch bad escapes early (Python):**
  ```pwsh
  $env:PYTHONWARNINGS='error::SyntaxWarning'
  python -X dev tools\py\pa_std_summary.py --level standard
  ```
- **Latest pack lives in:** `tmp\feedback\pack_project_snapshot_*.zip`
- **If you change tools,** rebuild the catalog before enriching packs:
  ```pwsh
  python tools\py\registry\build_tool_catalog.py --host 127.0.0.1 --port 8782
  python tools\py\pack\enrich_pack.py
  python tools\py\pack\verify_pack.py --include-meta --check-insights
  ```

---

## Support Bundle (diagnostics-first workflow)
Create a targeted bundle with code, logs, and HTTP captures:

```pwsh
.venv\Scripts\python.exe tools\py\pack\make_support_bundle.py `
  --outdir tmp\logs --name sb_next --add-logs --emit-ast `
  --include server\agent_actions_v7.py `
  --include server\agent_sidecar_wrapper.py `
  --include server\proposal_api.py `
  --include server\settings_api.py `
  --include tools\py\agentic\pilot_cli.py `
  --include tools\py\agentic\status.py `
  --include tools\py\agentic\drive_step.py `
  --include web\pwa\agent.html `
  --include web\pwa\settings_ext.js `
  --include web\pwa\agent_plan_v3.js `
  --include config\app_settings.json `
  --include project_plan_v3.yaml `
  --include project\tracker.yaml
```

**Use support bundles to drive changes:**  
1) Diagnose & capture (`/health`, `/__routes__`, served JS/CSS, logs).  
2) Propose a **line‑anchored patch** (with compile check).  
3) Apply.  
4) Smoke test.  
5) Re‑bundle for review.

---

## UI Change Safety (Lessons Learned)
- **Cache busting:** Always bump `agent.html` query string for `settings_ext.js` (e.g., `?v=3.9`) after modifying JS.
- **Served vs on‑disk:** Confirm `sha256` of **served** JS matches on‑disk; if not, hard refresh (Ctrl+F5) or increment `?v=`.
- **Avoid inline script regressions:** Prefer external `settings_ext.js`. If an inline helper exists, remove or ensure no duplication (e.g., avoid competing listeners or duplicate functions).
- **Selectors:** Use `$('section[data-pane="settings"]')` not raw `section[...]`. A corrupted selector can silently no‑op.
- **Listeners:** Verify counts with a regex on served JS (e.g., exactly one `btnApply.addEventListener('click', applyStep)`).
- **Mount hooks:** Ensure `DOMContentLoaded` **or** a fallback `load`/safety boot wrapper is present (idempotent).
- **Error telemetry:** Log console tags like `[ext-actions-v2]`, `[ext-safety]` around mounts and network calls.

---

## The Protocol (Ritual)
1. **Diagnose**  
   - Health: `/health` 200  
   - Routes: `/__routes__` (list endpoints)  
   - Fetch **served** assets (`/pwa/settings_ext.js`, `/pwa/agent`) and record hashes.  
   - Optional: run `mvp_smoke.py`.
2. **Request Files**  
   - Ask for a support bundle with the exact files you need to touch + relevant logs + HTTP captures.
3. **Propose Patch**  
   - Minimal, idempotent patch; anchors; compile check commands.
4. **Apply & Smoke Test**  
   - Re‑run health, routes, and a single UI exercise relevant to the change.  
   - Verify served JS reflects changes; bump `?v=` if needed.
5. **Package Evidence**  
   - `make_support_bundle.py` with the changed files + captures for auditability.
6. **Roll Forward or Revert**  
   - If green, proceed; if not, revert via backup or `git restore`.

---

## Appendix — Common One‑Liners
**Compare served vs on‑disk hash:**
```pwsh
# Served
$served = (Invoke-WebRequest http://127.0.0.1:8782/pwa/settings_ext.js -UseBasicParsing).Content
[BitConverter]::ToString((New-Object -TypeName System.Security.Cryptography.SHA256Managed).ComputeHash([Text.Encoding]::UTF8.GetBytes($served))).Replace('-','').ToLower()

# On-disk
Get-FileHash web\pwa\settings_ext.js -Algorithm SHA256 | % Hash
```

**Probe for mounts in served JS:**
```pwsh
$ext = (Invoke-WebRequest http://127.0.0.1:8782/pwa/settings_ext.js -UseBasicParsing).Content
$ext -match 'function\s+mountSettingsForm'
$ext -match 'function\s+mountActions'
$ext -match 'DOMContentLoaded'
```

**Routes filter:**
```pwsh
($routes = Invoke-RestMethod http://127.0.0.1:8782/__routes__).routes |
  ? rule -in "/agent/settings","/agent/propose","/agent/apply","/agent/summary"
```

---

## Final Notes
- **Work where you are sure.** If anything is ambiguous, re‑diagnose and get a targeted support bundle.
- **Every patch proves itself** (compile OK + smoke OK + served asset OK).
- **Keep it reversible.** Always create a backup file or commit before edit.
