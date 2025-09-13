def test_settings_get_set(monkeypatch, tmp_path):
    t = tmp_path / "tracker.yaml"
    t.write_text("project_id: t\nauto_revise:\n  enabled: true\n  default_iters: 1\n  ui_soft_max: 2\n", encoding="utf-8")
    monkeypatch.setenv("PROJECT_TRACKER", str(t))
    from server.settings_api import app
    c = app.test_client()
    r1 = c.get("/settings/auto_revise")
    assert r1.status_code == 200 and r1.get_json()["ok"]
    r2 = c.post("/settings/auto_revise", json={"default_iters": 3, "ui_soft_max": 4})
    j2 = r2.get_json()
    assert j2["ok"] and j2["limits"]["default_iters"] == 3 and j2["limits"]["ui_soft_max"] == 4
