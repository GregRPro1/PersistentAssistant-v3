from __future__ import annotations
import json, os, urllib.request, urllib.error
from pathlib import Path
from typing import Optional, Dict, Any
from .proposal_types import proposal_minimal_dict

def _http_post_json(url: str, payload: Dict[str, Any], timeout: float = 30.0) -> Dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))

def compose_proposal(step: str,
                     context: Optional[Dict[str, Any]] = None,
                     out_path: Optional[str] = None) -> str:
    """
    Return path to a JSON proposal. Try local agent HTTP if AGENT_BASE_URL is set; else write a stub.
    """
    base = os.environ.get("AGENT_BASE_URL")
    payload = {"step": step, "context": context or {}}
    proposal: Dict[str, Any] = proposal_minimal_dict()

    if base:
        try:
            proposal = _http_post_json(base.rstrip("/") + "/agent/compose", payload)
        except Exception:
            # Fall back to stub
            pass

    p = Path(out_path or (Path("tmp/agentic/proposals") / f"{step.replace('.', '_')}.json"))
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(proposal, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(p)
