import sys, subprocess, pathlib, os

def test_auto_next_minimal_plan(tmp_path):
    plan = tmp_path/"plan_min.yaml"
    plan.write_text(
        "steps:\n"
        "  - id: '10.4'\n"
        "    title: 'smoke step'\n"
        "    status: 'planned'\n"
        "    priority: 1\n",
        encoding="utf-8"
    )
    args = [
        sys.executable, "-m", "tools.py.agentic.auto_next",
        "--plan", str(plan),
        "--max", "1",
        "--tests", "tests/test_context_pack.py",
        "--pytest-flags", "-q"
    ]
    p = subprocess.run(args)
    assert p.returncode in (0,4)
