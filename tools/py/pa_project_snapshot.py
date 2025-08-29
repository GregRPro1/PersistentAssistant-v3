# tools/py/pa_project_snapshot.py
# One-shot, robust project snapshot pack for Persistent Assistant
# - Uses existing tools/structure_sync.py for structure snapshot
# - Python-only; invokes PowerShell only if auto_health.ps1 exists
# - Produces tmp\feedback\pack_project_snapshot_<ts>.zip

from __future__ import annotations
import os, sys, json, time, glob, shutil, zipfile, subprocess, traceback, py_compile, pathlib, platform

# ---------- helpers ----------

ROOT = pathlib.Path(__file__).resolve().parents[2]  # .../PersistentAssistant
TMP_DIR = ROOT / "tmp"
RUN_DIR = TMP_DIR / "run"
LOG_DIR = TMP_DIR / "logs"
FEEDBACK_DIR = TMP_DIR / "feedback"
TOOLS_DIR = ROOT / "tools"
STRUCTURE_SYNC = TOOLS_DIR / "structure_sync.py"
SHOW_NEXT_STEP = TOOLS_DIR / "show_next_step.py"
AUTO_HEALTH_PS1 = TOOLS_DIR / "auto_health.ps1"

def now_ts(fmt="%Y%m%d_%H%M%S") -> str:
    return time.strftime(fmt)

def ensure_dirs(*paths: pathlib.Path) -> None:
    for p in paths:
        p.mkdir(parents=True, exist_ok=True)

def write_text(path: pathlib.Path, text: str, enc="utf-8") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding=enc, errors="replace")

def write_json(path: pathlib.Path, obj: dict, enc="utf-8") -> None:
    write_text(path, json.dumps(obj, indent=2), enc=enc)

def run_proc(args: list[str], timeout: int = 30, cwd: pathlib.Path | None = None) -> dict:
    """
    Run a subprocess, capture stdout/stderr/rc. Never throws.
    """
    try:
        res = subprocess.run(
            args,
            cwd=str(cwd or ROOT),
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8",
            errors="replace",
        )
        return {
            "ok": (res.returncode == 0),
            "rc": res.returncode,
            "out": res.stdout,
            "err": res.stderr,
            "args": args,
        }
    except subprocess.TimeoutExpired as e:
        return {"ok": False, "rc": -9, "out": e.stdout or "", "err": f"TIMEOUT({timeout}s): {e}", "args": args}
    except Exception as e:
        return {"ok": False, "rc": -1, "out": "", "err": f"EXC: {e}", "args": args}

def which_powershell() -> str | None:
    # prefer Windows PowerShell if available, else pwsh
    for exe in ("powershell", "pwsh"):
        p = shutil.which(exe)
        if p:
            return p
    return None

def zip_dir(src_dir: pathlib.Path, dst_zip: pathlib.Path) -> None:
    if dst_zip.exists():
        dst_zip.unlink()
    with zipfile.ZipFile(dst_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(src_dir):
            for fn in files:
                fp = pathlib.Path(root) / fn
                arc = fp.relative_to(src_dir)
                zf.write(fp, arcname=str(arc))

# ---------- steps ----------

def step_env(stage: pathlib.Path) -> dict:
    info = {
        "python": sys.version,
        "executable": sys.executable,
        "platform": platform.platform(),
        "cwd": str(os.getcwd()),
    }
    try:
        from importlib.metadata import version, PackageNotFoundError
        info["flask_version"] = version("flask")
    except Exception:
        info["flask_version"] = None
    write_json(stage / "env.json", info)
    return info

def step_structure(stage: pathlib.Path) -> dict:
    res = {"ok": False, "out": "", "err": "", "rc": None}
    if STRUCTURE_SYNC.exists():
        r = run_proc([sys.executable, str(STRUCTURE_SYNC)], timeout=60)
        res.update(r)
    else:
        res["err"] = f"{STRUCTURE_SYNC} not found"
    write_json(stage / "structure_sync_result.json", res)
    # capture paths structure_sync normally writes
    res["expected_yaml"] = str(ROOT / "project" / "structure" / "project_structure_snapshot_full.yaml")
    res["expected_md"] = str(ROOT / "project" / "structure" / "project_structure_snapshot_index.md")
    for p in (res["expected_yaml"], res["expected_md"]):
        try:
            if pathlib.Path(p).exists():
                shutil.copy2(p, stage / pathlib.Path(p).name)
        except Exception:
            pass
    return res

def step_plan(stage: pathlib.Path) -> dict:
    if SHOW_NEXT_STEP.exists():
        r = run_proc([sys.executable, str(SHOW_NEXT_STEP)], timeout=20)
    else:
        r = {"ok": False, "rc": 127, "out": "", "err": f"{SHOW_NEXT_STEP} not found", "args": []}
    write_text(stage / "plan_step.txt", r.get("out", ""))
    write_text(stage / "plan_step.stderr.txt", r.get("err", ""))
    return r

def step_compile_stage(stage: pathlib.Path) -> dict:
    server_dir = ROOT / "server"
    results = []
    if server_dir.exists():
        for f in server_dir.rglob("*.py"):
            ok = True
            err = ""
            try:
                py_compile.compile(str(f), doraise=True)
            except Exception as e:
                ok = False
                err = "".join(traceback.format_exception_only(type(e), e)).strip()
            results.append({"file": str(f), "ok": ok, "err": err})
    write_json(stage / "py_compile.json", {"results": results})
    return {"count": len(results), "bad": [r for r in results if not r["ok"]]}

def step_import_wrapper(stage: pathlib.Path) -> dict:
    info = {"ok": True, "has_app": False, "file": None, "mode": None, "err": "", "trace": ""}
    try:
        # Try package import first
        import importlib
        m = importlib.import_module("server.agent_sidecar_wrapper")
        info["file"] = getattr(m, "__file__", None)
        info["has_app"] = bool(getattr(m, "app", None))
        info["mode"] = "package"
    except Exception as e1:
        info["ok"] = False
        info["err"] = str(e1)
        info["trace"] = traceback.format_exc()
        # Fallback: file import
        try:
            import importlib.util
            mod_path = ROOT / "server" / "agent_sidecar_wrapper.py"
            if mod_path.exists():
                spec = importlib.util.spec_from_file_location("agent_sidecar_wrapper_file", str(mod_path))
                mod = importlib.util.module_from_spec(spec)  # type: ignore
                assert spec and spec.loader
                spec.loader.exec_module(mod)  # type: ignore
                info = {
                    "ok": True,
                    "has_app": bool(getattr(mod, "app", None)),
                    "file": str(mod_path),
                    "mode": "file",
                    "err": "",
                    "trace": "",
                }
        except Exception as e2:
            info = {
                "ok": False,
                "has_app": False,
                "file": None,
                "mode": "fallback_file",
                "err": str(e2),
                "trace": traceback.format_exc(),
            }
    write_json(stage / "wrapper_import.json", info)
    return info

def step_auto_health(stage: pathlib.Path) -> dict:
    if not AUTO_HEALTH_PS1.exists():
        res = {"ok": False, "err": "tools/auto_health.ps1 not found"}
        write_json(stage / "endpoint_health.json", res)
        return res
    ps = which_powershell()
    if not ps:
        res = {"ok": False, "err": "No PowerShell (powershell/pwsh) in PATH"}
        write_json(stage / "endpoint_health.json", res)
        return res
    out_json = RUN_DIR / f"auto_health_{now_ts()}.json"
    args = [ps, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(AUTO_HEALTH_PS1), "-JsonOut", str(out_json)]
    r = run_proc(args, timeout=60)
    obj = {"runner": r, "json": None}
    try:
        if out_json.exists():
            obj["json"] = json.loads(out_json.read_text(encoding="utf-8", errors="replace"))
            shutil.copy2(out_json, stage / "endpoint_health.json")
    except Exception as e:
        obj["runner"]["ok"] = False
        obj["runner"]["err"] = f"{obj['runner'].get('err','')}\nJSON load error: {e}"
    return obj

def step_netstat_and_logs(stage: pathlib.Path) -> dict:
    # netstat
    ps = which_powershell() or "cmd"
    if ps.lower().endswith("powershell.exe") or ps.lower().endswith("pwsh"):
        net = run_proc([ps, "-NoProfile", "-Command", "netstat -ano"], timeout=10)
        write_text(stage / "netstat.txt", net.get("out", "") or net.get("err", ""))
    else:
        # Fallback to plain netstat via shell
        net = run_proc(["netstat", "-ano"], timeout=10)
        write_text(stage / "netstat.txt", net.get("out", "") or net.get("err", ""))

    # log tails
    copied = []
    if LOG_DIR.exists():
        logs = sorted(LOG_DIR.glob("*.log"), key=lambda p: p.stat().st_mtime, reverse=True)[:6]
        for p in logs:
            try:
                shutil.copy2(p, stage / p.name)
                copied.append(p.name)
            except Exception:
                pass
    return {"logs_copied": copied}

def step_repo_manifest(stage: pathlib.Path) -> dict:
    """
    Simple manifest of files (skip tmp/.venv/.git) so we don't drift on reality.
    """
    files = []
    skip_parts = {".git", "tmp", ".venv", "venv", "__pycache__"}
    for base, dirs, fns in os.walk(ROOT):
        rel_parts = set(pathlib.Path(base).parts)
        if rel_parts & skip_parts:
            continue
        for fn in fns:
            fp = pathlib.Path(base) / fn
            try:
                st = fp.stat()
                files.append({
                    "path": str(fp.relative_to(ROOT)).replace("\\", "/"),
                    "bytes": int(st.st_size),
                    "mtime": int(st.st_mtime),
                })
            except Exception:
                pass
    manifest = {"root": str(ROOT), "count": len(files), "files": files}
    write_json(stage / "repo_manifest.json", manifest)
    return {"count": len(files)}

# ---------- main ----------

def main() -> int:
    ensure_dirs(TMP_DIR, RUN_DIR, LOG_DIR, FEEDBACK_DIR)
    stamp = now_ts()
    stage = FEEDBACK_DIR / f"pack_project_snapshot_{stamp}.staging"
    ensure_dirs(stage)
    pack_zip = FEEDBACK_DIR / f"pack_project_snapshot_{stamp}.zip"

    # steps
    env = step_env(stage)
    structure_res = step_structure(stage)
    plan_res = step_plan(stage)
    compile_res = step_compile_stage(stage)
    import_res = step_import_wrapper(stage)
    health_res = step_auto_health(stage)
    net_logs = step_netstat_and_logs(stage)
    manifest_res = step_repo_manifest(stage)

    # summary
    status = "OK"
    bad_count = len(compile_res.get("bad", []))
    if bad_count > 0:
        status = "FAIL agent_compile_error"

    summary = {
        "stamp": stamp,
        "status": status,
        "env": env,
        "structure_sync": {
            "ok": structure_res.get("ok"),
            "rc": structure_res.get("rc"),
            "err": structure_res.get("err"),
            "expected_yaml": structure_res.get("expected_yaml"),
            "expected_md": structure_res.get("expected_md"),
        },
        "plan_probe": {
            "ok": plan_res.get("ok", False),
            "rc": plan_res.get("rc"),
            "err": plan_res.get("err"),
        },
        "compile": {
            "total": compile_res.get("count", 0),
            "bad_count": bad_count,
        },
        "wrapper_import": import_res,
        "endpoint_health_runner_ok": health_res.get("runner", {}).get("ok") if isinstance(health_res, dict) else None,
        "manifest_count": manifest_res.get("count"),
        "logs_copied": net_logs.get("logs_copied"),
        "paths": {
            "stage": str(stage),
            "zip": str(pack_zip),
        },
    }
    write_json(stage / "summary.json", summary)

    # zip
    zip_dir(stage, pack_zip)

    # print final line for operator
    print(f"PACK: {pack_zip.resolve()}")
    print(f"STATUS: {status}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
