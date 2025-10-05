import json, subprocess, sys, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]

def run(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True)
    return p.returncode, p.stdout, p.stderr

def test_patch_apply_dry_run_smoke():
    prop = ROOT / "tmp/patches/proposal_step_10_3.json"
    prop.parent.mkdir(parents=True, exist_ok=True)
    rc, out, err = run([sys.executable, "-m", "tools.py.agentic.propose_for_step", "--id", "10.3", "--out", str(prop), "--force"])
    assert rc == 0, err
    rc, out, err = run([sys.executable, "-m", "tools.py.agentic.patch_apply", "--proposal", str(prop)])
    assert rc == 0, err
    data = json.loads(out)
    assert data.get("ok") is True, data
    assert data.get("results"), data
    assert data["results"][0]["reason"] in ("would_apply", "applied")
