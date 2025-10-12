
import json, os
from pathlib import Path
from pal.core.ops import write_ops_snapshot
from pal.core.tunnel import _capture_url_from_output

def test_ops_snapshot_writes(tmp_path, monkeypatch):
    d = tmp_path / "proj"; d.mkdir()
    (d / "pal" / "config").mkdir(parents=True)
    (d / "reports" / "ops").mkdir(parents=True)
    (d / "pal" / "config" / "pal.yaml").write_text("web:\n  host: 127.0.0.1\n  port: 65535\n", encoding="utf-8")
    os.chdir(d)
    st = write_ops_snapshot(Path("pal/config/pal.yaml"))
    assert "web" in st and "phone" in st
    assert (Path("reports/ops/ops_status.json")).exists()

def test_capture_url_regex():
    assert _capture_url_from_output("Visit https://abc-xyz.trycloudflare.com now") == "https://abc-xyz.trycloudflare.com"
    assert _capture_url_from_output("no url here") is None
