import os, sys, json, tempfile, subprocess, shutil
from pathlib import Path

def run(cmd, env=None):
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
    out, err = p.communicate()
    return p.returncode, out.strip(), err.strip()

def main():
    repo = Path(__file__).resolve().parents[3]
    add = str(repo / "tools" / "py" / "registry" / "add_tool.py")
    tmpd = Path(tempfile.mkdtemp())
    try:
        overlay = tmpd / "overlay.yaml"
        env = dict(os.environ)
        env["PA_OVERLAY_PATH"] = str(overlay)

        # first add -> ok
        rc, out, err = run([sys.executable, add, "--kind","py","--ref","tools/py/pa_std_summary.py","--title","T"], env)
        assert rc == 0, (rc, out, err)

        # second add -> duplicate (rc=2)
        rc, out, err = run([sys.executable, add, "--kind","py","--ref","tools/py/pa_std_summary.py","--title","T2"], env)
        assert rc == 2, (rc, out, err)
        data = json.loads(out)
        assert data.get("error") == "duplicate_tool"

        # allow update -> ok
        env["PA_ALLOW_TOOL_UPDATE"] = "1"
        rc, out, err = run([sys.executable, add, "--kind","py","--ref","tools/py/pa_std_summary.py","--title","T3"], env)
        assert rc == 0, (rc, out, err)

        print("[OK] test_add_tool_guard")
        return 0
    finally:
        shutil.rmtree(tmpd, ignore_errors=True)

if __name__ == "__main__":
    sys.exit(main())
