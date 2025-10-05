import yaml, pathlib, sys

PLAN = pathlib.Path("project/plans/project_plan_v3.yaml")
if not PLAN.exists():
    print("[SKIP] plan file missing")
    raise SystemExit(0)

with open(PLAN, "r", encoding="utf-8") as f:
    d = yaml.safe_load(f) or {}

phases = d.setdefault("phases", [])
names = [p.get("name","") for p in phases]
if not any(str(n).startswith("Phase 7") for n in names):
    phases.append({
        "name": "Phase 7 – Remote Control MVP (Phone Workflow)",
        "steps": [
            {"id":"7.1","status":"planned","description":"Expose LEB /digest and /latest-pack endpoints (read-only) with token header"},
            {"id":"7.2","status":"planned","description":"Guardrails: forbid-forbidden scanner preflight on every apply; audit log of requests"},
            {"id":"7.3","status":"planned","description":"Auth v1: signed bearer token + IP allowlist + rate limiting"},
            {"id":"7.4","status":"planned","description":"Minimal mobile web client (PWA-lite) that fetches digest, displays latest PACK, lets user POST pre-approved action bundles"},
            {"id":"7.5","status":"planned","description":"Auth v2 hardening: device binding (public-key), one-time nonces, replay protection"},
            {"id":"7.6","status":"planned","description":"App polish + settings: LAN-only toggle, port rotation, emergency kill-switch, full audit viewer"}
        ]
    })
    d.setdefault("meta",{}).setdefault("current_step", d.get("meta",{}).get("current_step", "6.3"))
    print("[PLAN] Phase 7 inserted")
else:
    print("[PLAN] Phase 7 already present")

with open(PLAN, "w", encoding="utf-8") as f:
    yaml.safe_dump(d, f, sort_keys=False)
