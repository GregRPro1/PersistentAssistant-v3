from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

DEFAULT_STATUS_PATH = Path("data/runtime/agent_status.json")

def write_status(data: Dict[str, Any], path: Optional[str] = None) -> str:
    p = Path(path) if path else DEFAULT_STATUS_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    payload = dict(data)
    payload["timestamp"] = datetime.now(timezone.utc).isoformat()
    p.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(p)
