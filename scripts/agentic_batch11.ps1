param([switch]$Apply = $false)

Write-Host "==> Batch 11 (FIXED): Auto-revise loops + tracker + settings API"

# Prep
$dirs = @("project", "tools\py\agentic", "server", "tests")
foreach ($d in $dirs) { New-Item -ItemType Directory -Force -Path $d | Out-Null }

# 1) project/tracker.yaml (create if missing)
$tracker = "project\tracker.yaml"
if (-not (Test-Path $tracker)) {
    Write-Host "==> Write project\tracker.yaml (new)"
    @"
project_id: default-project
auto_revise:
  enabled: true
  default_iters: 1
  ui_soft_max: 5
"@ | Set-Content $tracker -Encoding UTF8
}
else { Write-Host "==> project\tracker.yaml exists (keeping)" }

# 2) policy editor helper (python module)
$polmod = "tools\py\agentic\policy_edit.py"
@"
from __future__ import annotations
import argparse, json, pathlib

def _read(p: pathlib.Path) -> str:
    return p.read_text(encoding='utf-8') if p.exists() else ''

def _write(p: pathlib.Path, s: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(s, encoding='utf-8')

def ensure_allow(path: pathlib.Path, globs: list[str]) -> dict:
    raw = _read(path)
    if "allow_globs:" not in raw:
        raw += "\nallow_globs:\n"
    lines = raw.splitlines()
    out = []
    in_allow = False
    existing = set()
    for ln in lines:
        if ln.strip().startswith("allow_globs:"):
            in_allow = True
            out.append(ln)
            continue
        if in_allow:
            if ln.strip().startswith("- "):
                out.append(ln)
                existing.add(ln.strip()[2:].strip().strip('"'))
                continue
            else:
                # leaving block
                for g in globs:
                    if g not in existing:
                        out.append(f'  - "{g}"')
                in_allow = False
                out.append(ln)
        else:
            out.append(ln)
    if in_allow:
        for g in globs:
            if g not in existing:
                out.append(f'  - "{g}"')
    new = "\n".join(out) + "\n"
    _write(path, new)
    return {"ok": True, "path": str(path), "added": [g for g in globs if g not in existing]}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default="config/runner_policy.yaml")
    ap.add_argument("--add-allow", nargs="+", default=[])
    args = ap.parse_args()
    res = ensure_allow(pathlib.Path(args.file), args.add_allow)
    print(json.dumps(res))
if __name__ == "__main__":
    main()
"@ | Set-Content $polmod -Encoding UTF8

Write-Host "==> Ensuring policy allow_globs include project/**"
python -m tools.py.agentic.policy_edit --file config/runner_policy.yaml --add-allow project/** | Write-Host

# 3) project_config.py (idempotent write/overwrite to keep latest)
@"
from __future__ import annotations
import os, pathlib, json
from typing import Any, Dict

ROOT = pathlib.Path(__file__).resolve()
REPO = ROOT.parents[3]

def _tracker_path() -> pathlib.Path:
    p = os.getenv("PROJECT_TRACKER")
    return pathlib.Path(p) if p else (REPO / "project" / "tracker.yaml")

def _read_yaml_or_json(path: pathlib.Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8")
    try:
        import yaml  # type: ignore
        data = yaml.safe_load(text) or {}
        return data if isinstance(data, dict) else {}
    except Exception:
        try:
            data = json.loads(text)
            return data if isinstance(data, dict) else {}
        except Exception:
            out: Dict[str, Any] = {}
            for line in text.splitlines():
                if ":" in line and not line.strip().startswith("#"):
                    k,v = line.split(":",1)
                    out[k.strip()] = v.strip()
            return out

def _ensure_nested(d: Dict[str, Any], key: str, default: Dict[str, Any]) -> None:
    if key not in d or not isinstance(d[key], dict):
        d[key] = dict(default)

def load_tracker() -> Dict[str, Any]:
    p = _tracker_path()
    d = _read_yaml_or_json(p)
    _ensure_nested(d, "auto_revise", {"enabled": True, "default_iters": 1, "ui_soft_max": 5})
    if "project_id" not in d:
        d["project_id"] = "default-project"
    return d

def save_tracker(new_cfg: Dict[str, Any]) -> None:
    p = _tracker_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    try:
        import yaml  # type: ignore
        text = yaml.safe_dump(new_cfg, sort_keys=False)
    except Exception:
        text = json.dumps(new_cfg, indent=2)
    p.write_text(text, encoding="utf-8")

def get_auto_revise_limits() -> Dict[str, Any]:
    cfg = load_tracker()
    ar = cfg.get("auto_revise", {}) or {}
    enabled    = bool(ar.get("enabled", True))
    default_it = int(ar.get("default_iters", 1))
    soft_max   = int(ar.get("ui_soft_max", 5))
    if default_it < 0: default_it = 0
    if soft_max   < 0: soft_max   = 0
    if default_it > soft_max: default_it = soft_max
    return {"enabled": enabled, "default_iters": default_it, "ui_soft_max": soft_max}

def set_auto_revise(enabled: bool | None = None, default_iters: int | None = None, ui_soft_max: int | None = None) -> Dict[str, Any]:
    cfg = load_tracker()
    ar = cfg.get("auto_revise", {}) or {}
    if enabled is not None: ar["enabled"] = bool(enabled)
    if default_iters is not None: ar["default_iters"] = int(default_iters)
    if ui_soft_max   is not None: ar["ui_soft_max"]   = int(ui_soft_max)
    cfg["auto_revise"] = ar
    limits = get_auto_revise_limits()
    ar["enabled"] = limits["enabled"]
    ar["default_iters"] = limits["default_iters"]
    ar["ui_soft_max"]   = limits["ui_soft_max"]
    save_tracker(cfg)
    return cfg
"@ | Set-Content tools\py\agentic\project_config.py -Encoding UTF8

# 4) drive_step.py with retries integration (overwrite to ensure latest)
@"
from __future__ import annotations
import argparse, json, os, subprocess, sys, time, pathlib, urllib.request, urllib.error

ROOT = pathlib.Path(__file__).resolve().parents[3]
DEFAULT_LEB = os.getenv("LEB_URL", "http://127.0.0.1:8765")

def _print(obj: dict) -> None:
    print(json.dumps(obj, ensure_ascii=False))

def leb_run(cmd: str, base: str = DEFAULT_LEB, timeout: float = 60.0) -> dict:
    url = base.rstrip("/") + "/run"
    payload = json.dumps({"cmd": cmd}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw)
    except Exception as e:
        if cmd.strip().startswith("pytest"):
            try:
                p = subprocess.run(cmd.split(), capture_output=True, text=True)
                return {"ok": True, "rc": p.returncode, "stdout": p.stdout, "stderr": p.stderr, "fallback": "local"}
            except Exception as e2:
                return {"ok": False, "error": f"local_pytest_failed: {type(e2).__name__}: {e2}"}
        return {"ok": False, "error": f"leb_failed: {type(e).__name__}: {e}"}

def propose_step(step: str, out_path: str | None = None) -> str:
    args = [sys.executable, "-m", "tools.py.agentic.propose_for_step", "--id", step]
    if out_path:
        args += ["--out", out_path]
    args += ["--force"]
    p = subprocess.run(args, capture_output=True, text=True)
    for line in (p.stdout + "\n" + p.stderr).splitlines():
        s = line.strip()
        if s.endswith(".json"):
            return s
    if out_path:
        return out_path
    raise SystemExit("proposal_path_not_found")

def apply_proposal(prop: str, really_apply: bool = False, base: str = DEFAULT_LEB) -> dict:
    ra = " --really-apply" if really_apply else ""
    cmd = f'python -m tools.py.agentic.patch_apply --proposal "{prop.replace("\\\\","/")}"{ra}'
    r = leb_run(cmd, base=base)
    if isinstance(r, dict) and r.get("stdout"):
        try:
            return json.loads(r["stdout"])
        except Exception:
            pass
    return r if isinstance(r, dict) else {"ok": False, "error": "invalid_response"}

def run_pytests(tests: list[str], flags: list[str] | None = None, base: str = DEFAULT_LEB) -> dict:
    flags = flags or []
    cmd = "pytest " + " ".join(flags + tests)
    return leb_run(cmd, base=base)

def _bounded_retries(requested: int | None) -> int:
    from tools.py.agentic.project_config import get_auto_revise_limits
    limits = get_auto_revise_limits()
    if not limits.get("enabled", True):
        return 0
    default_iters = int(limits.get("default_iters", 1))
    soft_max      = int(limits.get("ui_soft_max", 5))
    req = default_iters if requested is None else int(requested)
    if req < 0: req = 0
    if req > soft_max: req = soft_max
    return req

def drive(step: str, tests: list[str], flags: list[str], really_apply: bool, retries: int | None = None, base: str = DEFAULT_LEB) -> int:
    attempts = 0
    max_retries = _bounded_retries(retries)
    while True:
        attempts += 1
        out = str(ROOT / "tmp" / "patches" / f"proposal_step_{step.replace('.','_')}.json")
        pathlib.Path(out).parent.mkdir(parents=True, exist_ok=True)
        ppath = propose_step(step, out)
        _print({"ok": True, "phase": "propose", "prop": ppath, "elapsed_s": 0.0})

        apply_res = apply_proposal(ppath, really_apply=really_apply, base=base)
        ok_flag = bool(apply_res.get("ok", False))
        results = apply_res.get("results") or []
        _print({"ok": ok_flag, "phase": "apply", "dry_run": not really_apply, "really_apply": bool(really_apply), "results": len(results), "elapsed_s": 0.0})
        if not ok_flag:
            if attempts <= max_retries:
                _print({"ok": False, "phase": "apply_failed", "attempt": attempts, "next_attempt": attempts+1})
                continue
            return 1

        py = run_pytests(tests, flags, base=base)
        rc = int(py.get("rc", 1 if not py.get("ok") else 0))
        _print({"ok": rc==0, "phase": "pytest_leb" if "rc" in py else "pytest_local", "rc": rc})
        if rc == 0:
            return 0
        if attempts <= max_retries:
            _print({"ok": False, "phase": "pytest_failed", "attempt": attempts, "next_attempt": attempts+1})
            continue
        return 4

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--step", required=True, help="Plan step id")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--tests", default="tests/test_context_pack.py")
    ap.add_argument("--pytest-flags", nargs="*", default=[])
    ap.add_argument("--retries", type=int, default=None)
    args = ap.parse_args()
    tests = args.tests.split() if isinstance(args.tests, str) else list(args.tests)
    flags = list(args.pytest_flags) if isinstance(args.pytest_flags, list) else []
    return drive(step=args.step, tests=tests, flags=flags, really_apply=args.apply, retries=args.retries)

if __name__ == "__main__":
    sys.exit(main())
"@ | Set-Content tools\py\agentic\drive_step.py -Encoding UTF8

# 5) settings API (idempotent)
@"
from __future__ import annotations
from flask import Flask, request, jsonify
from tools.py.agentic.project_config import get_auto_revise_limits, set_auto_revise, load_tracker

app = Flask(__name__)

@app.get("/settings/auto_revise")
def get_ar():
    lim = get_auto_revise_limits()
    cfg = load_tracker()
    return jsonify({"ok": True, "limits": lim, "tracker": cfg})

@app.post("/settings/auto_revise")
def set_ar():
    j = request.get_json(force=True, silent=True) or {}
    en  = j.get("enabled")
    di  = j.get("default_iters")
    mx  = j.get("ui_soft_max")
    cfg = set_auto_revise(enabled=en, default_iters=di, ui_soft_max=mx)
    lim = get_auto_revise_limits()
    return jsonify({"ok": True, "limits": lim, "tracker": cfg})

if __name__ == "__main__":
    app.run("127.0.0.1", 5001, debug=False)
"@ | Set-Content server\settings_api.py -Encoding UTF8

# 6) tests
@"
import os, tempfile
from pathlib import Path

def test_tracker_defaults_and_setters(monkeypatch, tmp_path):
    p = tmp_path / "tracker.yaml"
    p.write_text("project_id: t\nauto_revise:\n  enabled: true\n  default_iters: 1\n  ui_soft_max: 2\n", encoding="utf-8")
    monkeypatch.setenv("PROJECT_TRACKER", str(p))
    from tools.py.agentic import project_config as pc
    cfg = pc.load_tracker()
    assert cfg["auto_revise"]["default_iters"] == 1
    assert cfg["auto_revise"]["ui_soft_max"] == 2
    pc.set_auto_revise(enabled=True, default_iters=3, ui_soft_max=4)
    lim = pc.get_auto_revise_limits()
    assert lim["default_iters"] == 3 and lim["ui_soft_max"] == 4
"@ | Set-Content tests\test_project_config.py -Encoding UTF8

@"
import importlib, tempfile
from pathlib import Path

def test_drive_auto_revise_loops(monkeypatch, tmp_path):
    t = tmp_path / "tracker.yaml"
    t.write_text("project_id: t\nauto_revise:\n  enabled: true\n  default_iters: 2\n  ui_soft_max: 3\n", encoding="utf-8")
    monkeypatch.setenv("PROJECT_TRACKER", str(t))
    ds = importlib.import_module("tools.py.agentic.drive_step")
    def fake_propose(step, out_path=None):
        p = Path(out_path or (tmp_path/"p.json"))
        p.write_text("{}", encoding="utf-8")
        return str(p)
    monkeypatch.setattr(ds, "propose_step", fake_propose)
    calls = {"pytest": 0}
    def fake_leb_run(cmd: str, base: str = "...", timeout: float = 60.0):
        if cmd.startswith("pytest"):
            calls["pytest"] += 1
            rc = 1 if calls["pytest"] == 1 else 0
            return {"ok": True, "rc": rc, "stdout": "", "stderr": ""}
        if "patch_apply" in cmd:
            tool = {"ok": True, "feature_id": "STEP-TEST", "dry_run": True, "results": [{"path":"X","ok":True}]}
            import json as _j
            return {"ok": True, "rc": 0, "stdout": _j.dumps(tool)}
        return {"ok": False, "error": "unexpected_cmd"}
    monkeypatch.setattr(ds, "leb_run", fake_leb_run)
    code = ds.drive(step="10.4", tests=["tests/test_context_pack.py"], flags=["-q"], really_apply=False, retries=None)
    assert code == 0 and calls["pytest"] == 2
"@ | Set-Content tests\test_drive_step_autorevise.py -Encoding UTF8

@"
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
"@ | Set-Content tests\test_settings_api.py -Encoding UTF8

# 7) Run tests
Write-Host "==> pytest -q tests/test_project_config.py"
& pytest -q tests/test_project_config.py
$rc1 = $LASTEXITCODE

Write-Host "==> pytest -q tests/test_drive_step_autorevise.py"
& pytest -q tests/test_drive_step_autorevise.py
$rc2 = $LASTEXITCODE

Write-Host "==> pytest -q tests/test_settings_api.py"
& pytest -q tests/test_settings_api.py
$rc3 = $LASTEXITCODE

if ($rc1 -eq 0 -and $rc2 -eq 0 -and $rc3 -eq 0) {
    Write-Host "==> Batch 11 complete (PASS)" -ForegroundColor Green
    exit 0
}
else {
    Write-Host "==> Batch 11 complete (FAIL $rc1,$rc2,$rc3)" -ForegroundColor Red
    exit 1
}
