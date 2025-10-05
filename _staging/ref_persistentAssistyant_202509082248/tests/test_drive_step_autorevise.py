import importlib, tempfile
from pathlib import Path

def test_drive_auto_revise_loops(monkeypatch, tmp_path):
    t = tmp_path / "tracker.yaml"
    t.write_text("project_id: t\nauto_revise:\n  enabled: true\n  default_iters: 2\n  ui_soft_max: 3\n", encoding="utf-8")
    monkeypatch.setenv("PROJECT_TRACKER", str(t))
    ds = importlib.import_module("tools.py.agentic.drive_step")
    def fake_propose(step, out_path=None):
        p = Path(out_path or (tmp_path/"p.json"))
        p.write_text("{}", encoding="utf-8")
        return str(p)
    monkeypatch.setattr(ds, "propose_step", fake_propose)
    calls = {"pytest": 0}
    def fake_leb_run(cmd: str, base: str = "...", timeout: float = 60.0):
        if cmd.startswith("pytest"):
            calls["pytest"] += 1
            rc = 1 if calls["pytest"] == 1 else 0
            return {"ok": True, "rc": rc, "stdout": "", "stderr": ""}
        if "patch_apply" in cmd:
            tool = {"ok": True, "feature_id": "STEP-TEST", "dry_run": True, "results": [{"path":"X","ok":True}]}
            import json as _j
            return {"ok": True, "rc": 0, "stdout": _j.dumps(tool)}
        return {"ok": False, "error": "unexpected_cmd"}
    monkeypatch.setattr(ds, "leb_run", fake_leb_run)
    code = ds.drive(step="10.4", tests=["tests/test_context_pack.py"], flags=["-q"], really_apply=False, retries=None)
    assert code == 0 and calls["pytest"] == 2
