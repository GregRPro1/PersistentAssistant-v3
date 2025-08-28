# tools/py/pa_diag_runner.py
# Creates a diagnostic pack and a one-line status for the PS wrapper (stdlib only).

import argparse, json, os, subprocess, sys, time, zipfile

REPO = os.path.abspath(os.getcwd())
TMP_FEEDBACK = os.path.join(REPO, "tmp", "feedback")
TMP_RUN = os.path.join(REPO, "tmp", "run")
TMP_LOGS = os.path.join(REPO, "tmp", "logs")
PLAN_FILE = os.path.join(REPO, "project", "plans", "project_plan_v3.yaml")

def ensure_dir(p): os.makedirs(p, exist_ok=True)

def run(cmd, cwd=None, timeout=20):
    try:
        cp = subprocess.run(cmd, cwd=cwd or REPO, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout, text=True, shell=False)
        return cp.returncode, cp.stdout, cp.stderr
    except Exception as e:
        return 99, "", str(e)

def read_show_step():
    py = os.path.join(REPO, "tools", "show_next_step.py")
    if not os.path.isfile(py):
        return {"id": "", "title": "", "raw": "", "ok": False}
    rc, out, err = run(["python", py])
    if rc == 0:
        try:
            j = json.loads(out)
            if "active_step" in j:
                a = j["active_step"]
                return {"id": str(a.get("id","")), "title": str(a.get("title","")), "raw": out, "ok": True}
        except Exception:
            pass
    first_line = (out.splitlines() + [""])[0]
    return {"id": "", "title": first_line.strip(), "raw": out or err, "ok": False}

def py_compile_files(paths):
    import py_compile, traceback
    res = []
    for p in paths:
        fp = os.path.join(REPO, p)
        try:
            py_compile.compile(fp, doraise=True)
            res.append({"file": p, "ok": True, "error": ""})
        except Exception as e:
            msg = "".join(traceback.format_exception_only(type(e), e)).strip()
            res.append({"file": p, "ok": False, "error": msg})
    return res

def env_versions():
    # Avoid importing flask to prevent DeprecationWarning on __version__.
    try:
        from importlib.metadata import version, PackageNotFoundError
    except Exception:
        # Py<3.8 backport not needed in your venv; fall back to empty values.
        return {"python": sys.version, "flask": "", "werkzeug": ""}
    def v(name):
        try:
            return version(name)
        except Exception:
            return ""
    return {"python": sys.version, "flask": v("flask"), "werkzeug": v("werkzeug")}

def latest_matching(dirpath, prefix):
    try:
        files = [os.path.join(dirpath, f) for f in os.listdir(dirpath) if f.startswith(prefix)]
        files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
        return files[0] if files else ""
    except Exception:
        return ""

def netstat_snapshot():
    rc, out, err = run(["netstat", "-ano"])
    return {"rc": rc, "stdout": out[-10000:], "stderr": err}

def pack_make(staging_dir, zip_path):
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for root, _, files in os.walk(staging_dir):
            for f in files:
                full = os.path.join(root, f)
                rel = os.path.relpath(full, staging_dir)
                z.write(full, rel)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    ensure_dir(TMP_FEEDBACK); ensure_dir(TMP_RUN); ensure_dir(TMP_LOGS)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    pack_name = f"pack_diag_{stamp}"
    staging = os.path.join(TMP_FEEDBACK, pack_name + ".staging")
    zip_path = os.path.join(TMP_FEEDBACK, pack_name + ".zip")
    ensure_dir(staging)

    # Plan snapshot (best effort)
    if os.path.isfile(PLAN_FILE):
        try:
            import shutil
            shutil.copy2(PLAN_FILE, os.path.join(staging, "plan_snapshot.yaml"))
        except Exception:
            pass

    # Step info
    step = read_show_step()

    # Compile diagnostics
    comp = py_compile_files(["server/agent_sidecar_wrapper.py", "server/serve_phone_clean.py"])

    # Logs tail (best-effort)
    def tail(p, n=200):
        try:
            with open(p, "r", encoding="utf-8", errors="replace") as f:
                return "".join(f.readlines()[-n:])
        except Exception:
            return ""

    sidecar_log = latest_matching(TMP_LOGS, "sidecar_")
    phone_log   = latest_matching(TMP_LOGS, "phone_")
    if sidecar_log:
        open(os.path.join(staging, "tail_sidecar.log"), "w", encoding="utf-8").write(tail(sidecar_log))
    if phone_log:
        open(os.path.join(staging, "tail_phone.log"), "w", encoding="utf-8").write(tail(phone_log))

    # Netstat
    ns = netstat_snapshot()
    open(os.path.join(staging, "netstat.txt"), "w", encoding="utf-8").write(ns["stdout"])

    # Summary
    summary = {
        "id": pack_name,
        "repo_root": REPO,
        "active_step": {"id": step["id"], "title": step["title"], "ok": step["ok"]},
        "env": env_versions(),
        "compile": comp,
        "errors": [],
    }
    open(os.path.join(staging, "summary.json"), "w", encoding="utf-8").write(json.dumps(summary, indent=2))

    # Make zip
    try:
        if os.path.isfile(zip_path): os.remove(zip_path)
        pack_make(staging, zip_path)
        pack_abs = os.path.abspath(zip_path)
    except Exception:
        pack_abs = "[NOT CREATED]"

    # Status from compile result
    status = "OK"
    if any(not c["ok"] for c in comp):
        status = "FAIL agent_compile_error"

    # Emit small OUT json for PS wrapper
    out = {"pack_path": pack_abs, "status": status}
    ensure_dir(os.path.dirname(args.out))
    open(args.out, "w", encoding="utf-8").write(json.dumps(out))
    return 0

if __name__ == "__main__":
    sys.exit(main())
