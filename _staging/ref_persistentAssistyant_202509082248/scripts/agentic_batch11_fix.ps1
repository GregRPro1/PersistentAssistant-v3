param([switch]$Apply = $false)

Write-Host "==> Batch 11 FIX: project_config normalization + proper save order"

$pc = "tools\py\agentic\project_config.py"
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

def _normalize_auto_revise(ar: Dict[str, Any]) -> Dict[str, Any]:
    en = bool(ar.get("enabled", True))
    try:
        di = int(ar.get("default_iters", 1))
    except Exception:
        di = 1
    try:
        sx = int(ar.get("ui_soft_max", 5))
    except Exception:
        sx = 5
    if di < 0: di = 0
    if sx < 0: sx = 0
    if di > sx: di = sx
    return {"enabled": en, "default_iters": di, "ui_soft_max": sx}

def load_tracker() -> Dict[str, Any]:
    p = _tracker_path()
    d = _read_yaml_or_json(p)
    _ensure_nested(d, "auto_revise", {"enabled": True, "default_iters": 1, "ui_soft_max": 5})
    d["auto_revise"] = _normalize_auto_revise(d["auto_revise"])
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
    ar = _normalize_auto_revise(cfg.get("auto_revise", {}))
    return dict(ar)

def set_auto_revise(enabled: bool | None = None, default_iters: int | None = None, ui_soft_max: int | None = None) -> Dict[str, Any]:
    cfg = load_tracker()
    ar  = dict(cfg.get("auto_revise", {}))
    if enabled is not None:
        ar["enabled"] = bool(enabled)
    if default_iters is not None:
        ar["default_iters"] = int(default_iters)
    if ui_soft_max is not None:
        ar["ui_soft_max"] = int(ui_soft_max)
    cfg["auto_revise"] = _normalize_auto_revise(ar)
    save_tracker(cfg)
    return cfg
"@ | Set-Content $pc -Encoding UTF8

Write-Host "==> pytest -q tests/test_project_config.py"
& pytest -q tests/test_project_config.py
$rc1 = $LASTEXITCODE

Write-Host "==> pytest -q tests/test_settings_api.py"
& pytest -q tests/test_settings_api.py
$rc2 = $LASTEXITCODE

Write-Host "==> pytest -q tests/test_drive_step_autorevise.py"
& pytest -q tests/test_drive_step_autorevise.py
$rc3 = $LASTEXITCODE

if ($rc1 -eq 0 -and $rc2 -eq 0 -and $rc3 -eq 0) {
    Write-Host "==> Batch 11 FIX complete (PASS)" -ForegroundColor Green
    exit 0
}
else {
    Write-Host "==> Batch 11 FIX complete (FAIL $rc1,$rc2,$rc3)" -ForegroundColor Red
    exit 1
}
