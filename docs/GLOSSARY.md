# Persistent Assistant — Glossary

This glossary defines the terms used across the Persistent Assistant codebase, UI, and scripts. It’s the shared language for the engineer and the agentic system.

## Core components

**Plan YAML (Single Source of Truth / SSoT)**  
`project\plans\project_plan_v3.yaml`. Contains phases and steps (IDs like `6.4.g`) with statuses (`planned`, `in_progress`, `done`, `blocked`, optional `warn`). The UI renders this tree and updates statuses via tools.

**Phase / Step IDs**  
Hierarchical dot notation: `6` → `6.4` → `6.4.g`. Letters suffix sub-steps (`a`, `b`, `c`). Sorting is “natural” (`6.4` before `6.10`). Parents are inferred from the ID prefix.

**Statuses (and UI colors)**  
- `done` — ✅ green  
- `in_progress` — ▶ amber  
- `planned` — ● blue  
- `blocked` — ✖ red  
- `warn` — ! yellow-amber (used sparingly)

**Sidecar Wrapper (agent_sidecar_wrapper.py)**  
A robust Flask wrapper that guarantees `/agent/*` endpoints exist even if the “real” sidecar isn’t present. It serves the PWA, fallback plan view, diagnostics, and optional blueprints. It makes bring-up reliable.

**Agent Sidecar (server/agent_sidecar.py)**  
The “real” app (if present). The wrapper will import and delegate to it. If missing, wrapper fallbacks ensure the UI still runs.

**PWA Agent UI**  
`web\pwa\agent.html` and its JS/CSS. Presents tabs (Summary, Plan, Next, Notes, Actions, Settings), plan tree, details panel, help, and status badges.

**Recent / Approvals**  
Lightweight flow to queue actions for human approval (or to show recent activity). Exposed via `/agent/recent`, `/agent/approvals_count`.

## Execution & automation

**LEB — Local Exec Bridge**  
A tiny local HTTP service (default `http://127.0.0.1:8765`) that runs commands safely on your machine and returns logs/artifacts. Endpoints include `/ping`, `/run`, `/logs`. Used by the Agentic Runner to execute tests, scripts, and tooling.

**Run Buckets (LEB profiles)**  
- **sanity** — fastest checks (lint, import, quick unit probes).  
- **targeted** — tests selected by impacted files/imports graph.  
- **smoke** — broader/test suite subset for confidence.

**Agentic Runner**  
The orchestration that turns a plan step into a safe patch via an ML-assisted loop (Planner → Editor → Verifier), using LEB to execute tests and tools, with human approval at decision points.

**Planner / Editor / Verifier (Tri-Agent Loop)**  
- **Planner**: clarifies the intent into a spec (acceptance & scope).  
- **Editor**: proposes a minimal patch (AST-first, diff fallback).  
- **Verifier**: selects/runs tests; summarizes failures; gates apply.

**AST (Abstract Syntax Tree)**  
Structured representation of source code. We use Python’s **LibCST** (or similar) to make safe, minimal edits before falling back to textual diffs.

**Unified Diff / Patch**  
The standard textual diff (unidiff) applied when AST edit isn’t feasible or when surfacing changes to humans.

**Preimage Check**  
Before applying a patch, verify the current file hash matches the expected base (preimage). Prevents clobbering concurrent/manual edits.

**Safe Replace**  
A file write protocol that checks preimage hash, backs up the original, writes the new file atomically, and records a manifest entry.

**Imports Graph**  
A quick scan of Python imports to estimate blast radius and pick **targeted** tests.

**Risk Score**  
Heuristic rating of a proposed patch: files_touched + hunks + import fanout + changed LOC + critical area tags + test delta. Used to require extra approval or split patches.

**Iteration Budget**  
Max number of Planner→Editor→Verifier cycles per run (e.g., 3). Prevents unbounded spend/time.

**Repro Bundle**  
A ZIP with diff, failing logs, junit, coverage, and a `repro.ps1` so anyone can rerun the exact scenario.

## CI / governance

**CI Parity**  
Local LEB buckets mirror GitHub Actions workflow. The same checks gate PRs. If it passes locally, it should pass on CI.

**Gate**  
A blocking policy (e.g., “CI must pass on PR to `main`”). The GUI reflects gate status; PRs fail if the gate is red.

**Budgets / Caps**  
Per-run and daily limits for tokens/$, iterations, files touched, hunks. Enforced by policy; surfaced in the UI (worker status/badges).

**Model Tiers**  
Fast (draft), Balanced (patch), Heavy (stuck/failing). The system escalates or de-escalates based on budget and difficulty.

**Cost Ledger**  
Daily JSON files tracking spend/tokens. Used to enforce budgets and for after-action reviews.

## Tools & artifacts

**Pack (Project Snapshot Pack)**  
Artifact bundle created by the reporting pipeline: manifests, structure indexes, insights, etc., under `tmp\feedback\pack_project_snapshot_*.zip`.

**Tool Catalog**  
Registry of scripts and endpoints (discoverable). Enables the agent to find and call tools consistently.

**Diagnostics**  
Scripts like `gui_diag.py`, `pa_std_summary.py`, `pa_project_snapshot.py` that check health, render structured summaries, and build packs.

**Watchdog**  
A scheduled health checker that pings endpoints, detects flapping, and notifies on failures.

**Phone Mini-Panel**  
A compact UI (mobile) to approve/apply/retry/stop agentic runs and see live counters.

