import importlib, json
from pathlib import Path

def test_pilot_status_and_feedback(monkeypatch, tmp_path):
    pilot = importlib.import_module("tools.py.agentic.pilot")
    ds = importlib.import_module("tools.py.agentic.drive_step")
    ai = importlib.import_module("tools.py.agentic.ai_link")

    captured_contexts = []
    def fake_compose(step, context=None, out_path=None):
        captured_contexts.append(dict(context or {}))
        p = Path(out_path or (tmp_path / "p.json"))
        p.write_text(json.dumps({"patches": []}), encoding="utf-8")
        return str(p)
    monkeypatch.setattr(ai, "compose_proposal", fake_compose)

    calls = {"pytest": 0}
    def fake_leb_run(cmd: str, base: str = "...", timeout: float = 60.0):
        if cmd.startswith("pytest"):
            calls["pytest"] += 1
            rc = 1 if calls["pytest"] == 1 else 0
            return {"ok": True, "rc": rc, "stdout": f"out{rc}", "stderr": f"err{rc}"}
        if "patch_apply" in cmd:
            return {"ok": True, "rc": 0, "stdout": "{}", "stderr": ""}
        return {"ok": False, "rc": 1, "stdout": "", "stderr": "unexpected"}
    monkeypatch.setattr(ds, "leb_run", fake_leb_run)

    status_file = tmp_path / "status.json"
    out_dir = tmp_path / "props"
    res = pilot.run_once(step="10.4", tests=["tests/test_context_pack.py"], flags=["-q"],
                         out_dir=str(out_dir), iters=2, status_path=str(status_file))
    assert res["ok"] is True
    assert status_file.exists()
    payload = json.loads(status_file.read_text(encoding="utf-8"))
    assert payload["phase"] == "test"
    assert payload["ok"] is True

    # feedback present on second attempt
    assert len(captured_contexts) >= 2
    assert "last_error" in captured_contexts[1]
    assert captured_contexts[1]["last_error"]["rc"] == 1
