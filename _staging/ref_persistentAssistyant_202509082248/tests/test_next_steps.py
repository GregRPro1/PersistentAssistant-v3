from pathlib import Path
import importlib

def test_next_steps_selects_lowest_priority(tmp_path):
    plan = tmp_path/"plan.yaml"
    plan.write_text(
        "steps:\n"
        "  - id: '20.1'\n"
        "    title: 'X'\n"
        "    status: 'planned'\n"
        "    priority: 5\n"
        "  - id: '10.4'\n"
        "    title: 'Y'\n"
        "    status: 'planned'\n"
        "    priority: 1\n",
        encoding="utf-8"
    )
    ns = importlib.import_module("tools.py.agentic.next_steps")
    nid = ns.select_next_step(str(plan), statuses=("planned","in_progress"))
    assert nid == "10.4"

def test_next_steps_none_when_no_match(tmp_path):
    plan = tmp_path/"plan.yaml"
    plan.write_text("steps:\n  - id: '1'\n    status: 'done'\n    priority: 1\n", encoding="utf-8")
    ns = importlib.import_module("tools.py.agentic.next_steps")
    assert ns.select_next_step(str(plan), statuses=("planned",)) is None
