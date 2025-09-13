from __future__ import annotations
from pathlib import Path
from typing import Iterable, Optional

try:
    import yaml
except Exception:
    yaml = None

def select_next_step(plan_path: str,
                     statuses: Iterable[str] = ("planned", "in_progress")) -> Optional[str]:
    """
    Return the id of the 'next' step from plan_path by:
      - filtering to 'statuses'
      - choosing the lowest numeric 'priority' (default very large if missing)
      - stable tie-break by input order
    Returns None if no match or YAML unavailable.
    """
    if yaml is None:
        return None
    p = Path(plan_path)
    if not p.exists():
        return None
    try:
        data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        steps = data.get("steps") or []
        wanted = {str(s).lower() for s in statuses}
        def key_fn(item):
            try:
                pr = int(item.get("priority", 1_000_000))
            except Exception:
                pr = 1_000_000
            return (pr,)
        candidates = [s for s in steps
                      if str(s.get("status","")).lower() in wanted and s.get("id")]
        if not candidates:
            return None
        candidates.sort(key=key_fn)  # stable sort preserves file order for ties
        return str(candidates[0]["id"])
    except Exception:
        return None
