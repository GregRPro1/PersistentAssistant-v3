import importlib, json
from pathlib import Path

def test_pilot_cli_run(monkeypatch, tmp_path):
    cli = importlib.import_module("tools.py.agentic.pilot_cli")
    ds = importlib.import_module("tools.py.agentic.drive_step")
    ai = importlib.import_module("tools.py.agentic.ai_link")

    def fake_compose(step, context=None, out_path=None):
        p = Path(out_path or (tmp_path / "p.json"))
        p.write_text(json.dumps({"patches": []}), encoding="utf-8")
        return str(p)
    monkeypatch.setattr(ai, "compose_proposal", fake_compose)

    calls = {"pytest": 0}
    def fake_leb_run(cmd: str, base: str = "...", timeout: float = 60.0):
        if cmd.startswith("pytest"):
            calls["pytest"] += 1
            rc = 1 if calls["pytest"] == 1 else 0
            return {"ok": True, "rc": rc, "stdout": "", "stderr": ""}
        if "patch_apply" in cmd:
            return {"ok": True, "rc": 0, "stdout": "{}", "stderr": ""}
        return {"ok": False, "rc": 1, "stdout": "", "stderr": "unexpected"}
    monkeypatch.setattr(ds, "leb_run", fake_leb_run)

    status_file = tmp_path / "status.json"
    out_dir = tmp_path / "props"
    rc = cli.run_cli([
        "--step","10.4",
        "--tests","tests/test_context_pack.py",
        "--iters","2",
        "--status", str(status_file),
        "--out-dir", str(out_dir)
    ])
    assert rc == 0
    assert status_file.exists()
    assert any(out_dir.iterdir())
