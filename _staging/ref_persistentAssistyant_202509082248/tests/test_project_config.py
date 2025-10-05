import os, tempfile
from pathlib import Path

def test_tracker_defaults_and_setters(monkeypatch, tmp_path):
    p = tmp_path / "tracker.yaml"
    p.write_text("project_id: t\nauto_revise:\n  enabled: true\n  default_iters: 1\n  ui_soft_max: 2\n", encoding="utf-8")
    monkeypatch.setenv("PROJECT_TRACKER", str(p))
    from tools.py.agentic import project_config as pc
    cfg = pc.load_tracker()
    assert cfg["auto_revise"]["default_iters"] == 1
    assert cfg["auto_revise"]["ui_soft_max"] == 2
    pc.set_auto_revise(enabled=True, default_iters=3, ui_soft_max=4)
    lim = pc.get_auto_revise_limits()
    assert lim["default_iters"] == 3 and lim["ui_soft_max"] == 4
