import importlib, json
from pathlib import Path

def test_pilot_stub_minimal(monkeypatch, tmp_path):
    pilot = importlib.import_module("tools.py.agentic.pilot")
    ds = importlib.import_module("tools.py.agentic.drive_step")
    ai = importlib.import_module("tools.py.agentic.ai_link")

    # AI returns a trivial proposal file
    def fake_compose(step, context=None, out_path=None):
        p = Path(out_path or (tmp_path / "p.json"))
        p.write_text(json.dumps({"patches": []}), encoding="utf-8")
        return str(p)
    monkeypatch.setattr(ai, "compose_proposal", fake_compose)

    # leb_run simulates pytest: fail first, pass second
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

    out_dir = tmp_path / "props"
    res = pilot.run_once(step="10.4", tests=["tests/test_context_pack.py"], flags=["-q"], out_dir=str(out_dir), iters=2)
    assert res["ok"] is True
    assert res["rc"] == 0
    # at least one proposal file created
    assert any(out_dir.iterdir())
