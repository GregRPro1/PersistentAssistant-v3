
# -*- coding: utf-8 -*-
This file contains only the patched helpers used by settings save.
Integrate into existing watchdog_ui_basic.py.

from pathlib import Path
import io
import os
import yaml

SETTINGS_PATH = Path(r"C:\_Repos\PersistentAssistant\config\pal_settings.yaml")

def _load_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

def _dump_yaml(path: Path, data: dict) -> None:
    # Ensure parent exists
    path.parent.mkdir(parents=True, exist_ok=True)
    # Dump with safe_dump; keep keys order stable
    with path.open("w", encoding="utf-8", newline="\n") as f:
        yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)

def normalize_windows_path(p: str) -> str:
    # Accept raw input; return canonical absolute path with backslashes preserved
    p = p.strip().strip('"').strip("'")
    return str(Path(p)).replace('/', '\\')

def save_settings_number_and_tracker(whatsapp_number: str, tracker_script: str) -> None:
    cfg = _load_yaml(SETTINGS_PATH)

    # Create nested maps if missing
    cfg.setdefault('whatsapp', {})
    cfg.setdefault('paths', {})

    # Normalize values
    whatsapp_number = (whatsapp_number or '').strip().replace(' ', '')
    tracker_script = normalize_windows_path(tracker_script)

    cfg['whatsapp']['number'] = whatsapp_number
    cfg['paths']['tracker_script'] = tracker_script

    _dump_yaml(SETTINGS_PATH, cfg)

# Example direct invocation for manual test (won't run under Flask unless called)
if __name__ == "__main__":
    # Safe test
    save_settings_number_and_tracker("447XXXXXXXXX", r"C:\_Repos\PersistentAssistant\config\pal_tracker.py")
    print("Saved OK to", SETTINGS_PATH)

# === PAL20251012B HOTFIX START (yaml-save, no-regex) ===
from pathlib import Path as _PA_Path
import yaml as _PA_yaml

_PA_SETTINGS_PATH = _PA_Path(r"C:\_Repos\PersistentAssistant\config\pal_settings.yaml")

def _pa_load_yaml(_p):
    try:
        return _PA_yaml.safe_load(_PA_Path(_p).read_text(encoding="utf-8")) or {}
    except Exception:
        return {}

def _pa_dump_yaml(_p, _data):
    _p = _PA_Path(_p)
    _p.parent.mkdir(parents=True, exist_ok=True)
    _p.write_text(_PA_yaml.safe_dump(_data, sort_keys=False, allow_unicode=True), encoding="utf-8")

def _pa_norm_win_path(p: str) -> str:
    if p is None:
        return ""
    p = str(p).strip().strip('"').strip("'")
    return str(_PA_Path(p)).replace("/", "\\")

def upsert(section: str, key: str, value: str):
    # Override original regex-based upsert with safe YAML write
    cfg = _pa_load_yaml(_PA_SETTINGS_PATH)
    if section not in cfg or not isinstance(cfg.get(section), dict):
        cfg[section] = {}
    if key == "tracker_script":
        value = _pa_norm_win_path(value)
    if key == "number":
        value = (value or "").replace(" ", "")
    cfg[section][key] = value
    _pa_dump_yaml(_PA_SETTINGS_PATH, cfg)

def save_settings_number_and_tracker(number: str, tracker: str):
    # Normalize and persist both fields
    upsert("whatsapp", "number", number)
    upsert("paths", "tracker_script", tracker)
# === PAL20251012B HOTFIX END ===

# === PAL20251012B YAML-SAVE HOTFIX (no-regex) ===
try:
    from pathlib import Path as _PA_Path
    import yaml as _PA_yaml
    _PA_SETTINGS_PATH = _PA_Path(r"C:\_Repos\PersistentAssistant\config\pal_settings.yaml")

    def _pa_load_yaml(_p):
        try:
            return _PA_yaml.safe_load(_PA_Path(_p).read_text(encoding="utf-8")) or {}
        except Exception:
            return {}

    def _pa_dump_yaml(_p, _data):
        _p = _PA_Path(_p)
        _p.parent.mkdir(parents=True, exist_ok=True)
        _p.write_text(_PA_yaml.safe_dump(_data, sort_keys=False, allow_unicode=True), encoding="utf-8")

    def _pa_norm_win_path(p: str) -> str:
        if p is None:
            return ""
        p = str(p).strip().strip('"').strip("'")
        return str(_PA_Path(p)).replace("/", "\")

    def upsert(section: str, key: str, value: str):
        cfg = _pa_load_yaml(_PA_SETTINGS_PATH)
        if section not in cfg or not isinstance(cfg.get(section), dict):
            cfg[section] = {}
        if key == "tracker_script":
            value = _pa_norm_win_path(value)
        if key == "number":
            value = (value or "").replace(" ", "")
        cfg[section][key] = value
        _pa_dump_yaml(_PA_SETTINGS_PATH, cfg)

    def save_settings_number_and_tracker(number: str, tracker: str):
        upsert("whatsapp", "number", number)
        upsert("paths", "tracker_script", tracker)
except Exception as _e:
    # Do not break server if hotfix fails to import
    pass
# === END HOTFIX ===
