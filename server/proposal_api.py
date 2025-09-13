# server/proposal_api.py
from __future__ import annotations

import json
import time
from typing import Any, Dict

from flask import Blueprint, request, jsonify

bp = Blueprint("proposal_api", __name__, url_prefix="/agent")


def _call_next2() -> Dict[str, Any]:
    """
    Best-effort helper: call the existing /agent/next2 handler in-process
    (server.agent_actions_v7.agent_next2) to keep one source of truth for
    proposed next steps. Falls back to a static list if anything fails.
    """
    try:
        # Import lazily to avoid hard dependency if the module is absent.
        from server.agent_actions_v7 import agent_next2  # type: ignore

        resp = agent_next2()
        # Normalize common Flask return shapes
        if isinstance(resp, tuple):
            resp = resp[0]
        if hasattr(resp, "get_data"):
            data = json.loads(resp.get_data(as_text=True))
        elif isinstance(resp, dict):
            data = resp
        else:
            try:
                data = json.loads(str(resp))
            except Exception:
                data = {}

        if isinstance(data, dict):
            ok = bool(data.get("ok", False))
            suggestions = data.get("suggestions") or []
            if ok and isinstance(suggestions, list):
                return {"ok": True, "suggestions": suggestions, "ts": int(time.time()), "source": "next2"}
    except Exception:
        # Swallow and fall back
        pass

    # Fallback: deterministic suggestions (match your historical values)
    return {
        "ok": True,
        "suggestions": ["9.5a — Worker UX", "9.5b — Auto-process", "9.5c — Plan details"],
        "ts": int(time.time()),
        "source": "fallback",
    }


@bp.route("/propose", methods=["GET", "POST"])
def agent_propose():
    """
    GET  -> returns proposed next steps (delegates to next2 when available)
    POST -> accepts/rejects a proposed step or set of steps

    POST body (examples):
      {"accept": true, "step": "4.1"}
      {"decision": "accept", "steps": ["4.1","4.2"], "note": "Looks good"}

    Response:
      {"ok": true, "accepted": true/false, "step": "...", "steps": [...], "ts": ...}
    """
    if request.method == "POST":
        payload = request.get_json(silent=True) or {}
        # Normalize decision
        decision = payload.get("decision")
        if decision is None:
            # Support boolean flags used by the UI
            if "accept" in payload:
                decision = "accept" if payload.get("accept") else "reject"
        decision = (str(decision or "")).strip().lower()

        accepted = decision in ("accept", "accepted", "yes", "y", "true", "1")
        step = payload.get("step")
        steps = payload.get("steps") if isinstance(payload.get("steps"), list) else None
        note = payload.get("note")

        # Here is where you’d persist acceptance (e.g., write an approval file,
        # update tracker.yaml, enqueue a worker job, etc). For now we just ack.
        return jsonify({
            "ok": True,
            "accepted": bool(accepted),
            "step": step,
            "steps": steps,
            "note": note,
            "ts": int(time.time())
        })

    # GET: return suggestions
    return jsonify(_call_next2())
