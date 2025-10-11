# PAL Rebuild Plan (v0.1.0) — 2025-10-11

**PAL = Persistent Assistant Lite.** Objective: deliver a lean, reliable, agent-assisted development platform with a rock-solid **phone/web control surface**, YAML SSOT, and **remote approvals**. We keep the strengths and drop the drag.

---

## North Star
- Phone/laptop UI shows **color-coded YAML task tree**, approvals, notes, and ideas.
- From cold boot or upgrade, system is **ready in ≤20s**; if not, **auto-rollback**.
- Every change flows: **Docs → YAML (SSOT) → Planned work items → Execute (agent) → Validate → Remote Approve → PR**.

## Repo Strategy (Strangler Pattern)
- New clean root under `/pal/**`; quarantine legacy under `/legacy/**`.
- CI only targets `/pal/**`.
- Harvest old utilities *only when needed* and only with tests.

### Layout
```
/pal/
  core/         # schemas, validators, health
  pipelines/    # doc→yaml, plan/chunk, execute, validate, PR
  adapters/
    llm/        # provider-agnostic ChatGPT/Claude/etc.
    vcs/        # GitHub checks/status/env approvals
  ui/
    web/        # FastAPI + WebSocket; phone & laptop
    desktop/    # minimal launcher (optional)
  scripts/ps/   # PowerShell wrappers
  ci/           # workflows & tests
/legacy/        # quarantined old code for harvesting
PA_CONSTITUTION.md
```

## Releases & Rollback
- Each release in `releases/pal-X.Y.Z/` with `run.ps1`, `health.ps1`, `env.json`.
- `current` is a **junction** to the active release.
- **Watchdog** runs every minute:
  1. On upgrade, grant 20 seconds to pass `GET /healthz` and WS connect.
  2. If fail, relink `current` to last `_good` and restart; log to EventLog.
- Mark a good release by creating `releases/pal-X.Y.Z/_good` after smoke tests.

## Health Model
- `GET /healthz` returns 200 + JSON: `{"version":"X.Y.Z","uptime":...}`.
- WebSocket `/ws/:projectId` connects and receives a heartbeat within 5s.
- YAML watcher emits diff events; UI updates the tree live.

## Approvals
- Primary: **phone/web Approve** button → backend sets GitHub **commit status/check**.
- Optional secondary: GitHub **Environment approvals** as belt-and-braces.

## Testing & CI Gates
- Unit: schemas, atomic IO, status transitions.
- API: `/healthz`, `/projects/:id/tree` round-trip.
- WS: connect + receive diff on file change.
- E2E: boot ≤20s; intentional-bad-release triggers rollback.
- CI blocks merge if any gate fails; files must include headers.

## Phases (see YAML for details)
- **M0 — Phone/Web Link Reliability** (finish the small bits first)  
- **P1 — Cutover & SSOT Hardening**  
- **P2 — Phone/Web UX & Workflow**  
- **P3 — Agentic Execution (Adapters)**  
- **P4 — Telemetry & Harvest**  
- **P5 — Spec-Kit Bridge (Optional)**  
- **P6 — Desktop Base App (Optional)**

## Success Metrics
- ≥30% fewer rework commits/PR; 100% PRs gated by tests+schema+headers+approval.
- Median PR lead-time down 25%.
- Cold boot to ready ≤20s validated in CI.

## Kill Switch
- If metrics fail for two sprints, pause new features; focus on stability and SSOT quality until green.
