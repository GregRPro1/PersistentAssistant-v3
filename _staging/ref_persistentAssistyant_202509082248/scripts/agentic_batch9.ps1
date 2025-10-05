param([switch]$Apply = $false)

Write-Host "==> Batch 9 (FIXED): Strategy selector + tests"

New-Item -ItemType Directory -Force -Path "tools\py\agentic" | Out-Null
New-Item -ItemType Directory -Force -Path "tests" | Out-Null

@"
from __future__ import annotations
from typing import Any, Dict, List
import pathlib

def _yaml_load(text: str) -> Dict[str, Any]:
    try:
        import yaml  # type: ignore
        data = yaml.safe_load(text) or {}
        return data if isinstance(data, dict) else {}
    except Exception:
        # Minimal parser for:
        # steps:
        #   - id: '10.4'
        #     title: ...
        #     status: ...
        #     priority: 1
        steps: List[Dict[str, Any]] = []
        cur: Dict[str, Any] | None = None
        in_steps = False
        for raw in text.splitlines():
            line = raw.rstrip()
            if line.strip().startswith("#"): continue
            if line.strip() == "steps:":
                in_steps = True
                continue
            if not in_steps: continue
            if line.strip().startswith("- "):
                if cur: steps.append(cur)
                cur = {}
                tail = line.strip()[2:]
                if ":" in tail:
                    k,v = tail.split(":",1)
                    cur[k.strip()] = v.strip().strip("'\"")
                continue
            if cur is not None and ":" in line and line.startswith("  "):
                k,v = line.strip().split(":",1)
                val = v.strip().strip("'\"")
                # ints if possible
                try:
                    ival = int(val)
                    cur[k] = ival
                except Exception:
                    cur[k] = val
        if cur: steps.append(cur)
        return {"steps": steps}

def load_plan(path: pathlib.Path | str) -> Dict[str, Any]:
    p = pathlib.Path(path)
    text = p.read_text(encoding="utf-8")
    return _yaml_load(text)

_STATUS_ORDER = {"in_progress": 0, "planned": 1, "blocked": 9, "done": 99}

def rank_candidates(plan: Dict[str, Any]) -> List[Dict[str, Any]]:
    steps = plan.get("steps") or []
    ranked = []
    for s in steps:
        st  = str(s.get("status","planned")).lower()
        pri = int(s.get("priority", 5))
        if st not in _STATUS_ORDER: continue
        score = ( _STATUS_ORDER[st], -pri )  # lower tuple sorts first
        ranked.append({"id": s.get("id"), "title": s.get("title"), "status": st, "priority": pri, "score": score})
    ranked.sort(key=lambda x: x["score"])
    return ranked

def pick_next(plan: Dict[str, Any]) -> Dict[str, Any] | None:
    ranked = rank_candidates(plan)
    return ranked[0] if ranked else None
"@ | Set-Content tools\py\agentic\next_steps.py -Encoding UTF8

@"
from tools.py.agentic.next_steps import load_plan, rank_candidates, pick_next

def test_pick_next_minimal(tmp_path):
    plan = tmp_path / "plan.yaml"
    plan.write_text(
        "steps:\n"
        "  - id: '10.4'\n"
        "    title: 'smoke step'\n"
        "    status: 'planned'\n"
        "    priority: 2\n"
        "  - id: '10.5'\n"
        "    title: 'other step'\n"
        "    status: 'in_progress'\n"
        "    priority: 1\n",
        encoding="utf-8"
    )
    data = load_plan(plan)
    ranks = rank_candidates(data)
    assert ranks
    # in_progress beats planned regardless of priority
    assert ranks[0]["id"] == "10.5"
    nxt = pick_next(data)
    assert nxt["id"] == "10.5"
"@ | Set-Content tests\test_next_steps.py -Encoding UTF8

Write-Host "==> pytest -q tests/test_next_steps.py"
& pytest -q tests/test_next_steps.py
if ($LASTEXITCODE -eq 0) {
    Write-Host "==> Batch 9 complete (PASS)" -ForegroundColor Green
    exit 0
}
else {
    Write-Host "==> Batch 9 complete (FAIL $LASTEXITCODE)" -ForegroundColor Red
    exit 1
}
