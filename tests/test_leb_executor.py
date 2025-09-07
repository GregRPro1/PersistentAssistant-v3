import json, importlib
from pathlib import Path

def test_leb_run_patch_apply_dry_and_apply(tmp_path):
    ds = importlib.import_module("tools.py.agentic.drive_step")

    # create a proposal that adds a file then modifies it
    proposal = tmp_path / "p.json"
    proposal.write_text(json.dumps({
        "patches": [
            {"action": "add", "path": "tmp_out/hello.txt", "content": "hi"},
            {"action": "modify", "path": "tmp_out/hello.txt", "content": "bye"},
        ]
    }), encoding="utf-8")

    # dry-run
    res1 = ds.leb_run(f"patch_apply --dry-run {proposal}")
    assert res1["ok"] and res1["rc"] == 0
    out_file = Path("tmp_out/hello.txt")
    assert not out_file.exists()

    # apply
    res2 = ds.leb_run(f"patch_apply --apply {proposal}")
    assert res2["ok"] and res2["rc"] == 0
    assert out_file.exists()
    assert out_file.read_text(encoding="utf-8") == "bye"
    # clean up
    out_file.unlink()
