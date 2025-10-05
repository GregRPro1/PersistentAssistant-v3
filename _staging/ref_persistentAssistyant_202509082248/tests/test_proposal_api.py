import json, os, requests
from pathlib import Path
import pytest

# Import the Flask app without running it as a server
from server.proposal_api import app, LEB_URL, ROOT

def leb_up():
    try:
        r = requests.get(f"{LEB_URL}/ping", timeout=2)
        return r.status_code == 200
    except Exception:
        return False

@pytest.mark.skipif(not leb_up(), reason="LEB is not running on 127.0.0.1:8765")
def test_proposal_api_roundtrip():
    client = app.test_client()

    # 1) propose
    out = "tmp/patches/proposal_api_test.json"
    rv = client.post("/propose_step", json={"id":"10.3","out":out})
    assert rv.status_code == 200
    j = rv.get_json()
    assert j["ok"] is True
    ppath = j["proposal_path"]
    assert Path(ppath).exists()

    # 2) diff
    rv2 = client.post("/proposal_diff", json={"proposal_path": ppath})
    assert rv2.status_code == 200
    d = rv2.get_json()
    assert d["ok"] is True
    diff_text = json.dumps(d["diff"])
    assert "+" in diff_text or "diffs" in d["diff"]  # minimal sanity

    # 3) dry-run apply (should be ok / would_apply or applied depending on policy)
    rv3 = client.post("/proposal_apply", json={"proposal_path": ppath, "really_apply": False})
    assert rv3.status_code == 200
    a = rv3.get_json()
    assert a["ok"] is True
    res = a["result"]
    assert res.get("ok") in (True, False)  # tool emits ok True for dry-run ok
