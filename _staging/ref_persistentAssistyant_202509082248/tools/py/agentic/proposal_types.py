from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

@dataclass
class Patch:
    path: str
    action: str = "modify"           # modify|add|delete|rename
    content: Optional[str] = None
    from_path: Optional[str] = None

@dataclass
class Proposal:
    title: Optional[str] = None
    summary: Optional[str] = None
    patches: List[Patch] = field(default_factory=list)
    notes: Dict[str, Any] = field(default_factory=dict)

def proposal_minimal_dict() -> Dict[str, Any]:
    return {"title": None, "summary": None, "patches": [], "notes": {}}
