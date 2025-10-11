"""
GitHub checks/status abstraction (stub).
In real usage, implement create_check, set_status, etc.
"""
from typing import Optional

def set_commit_status(sha: str, state: str, context: str="pal", target_url: Optional[str]=None, description: str="") -> bool:
    # Stub: Log/print-only; return True.
    print(f"[vcs-stub] set_commit_status sha={sha} state={state} ctx={context}")
    return True
