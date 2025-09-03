import json, subprocess, sys, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]

def run(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True)
    return p.returncode, p.stdout, p.stderr

def test_context_pack_smoke():
    out = ROOT / "tmp/context/context_pack.json"
    if out.exists():
        out.unlink()
    rc, out_str, err = run([sys.executable, "-m", "tools.py.agentic.context_pack", "--out", str(out)])
    assert rc == 0, err
    assert out.exists(), "context pack json not created"
    data = json.loads(out.read_text(encoding="utf-8"))
    assert "files" in data and isinstance(data["files"], list)
    rels = { f["rel"] for f in data["files"] }
    assert "project/plans/project_plan_v3.yaml" in rels
    assert "config/runner_policy.yaml" in rels
