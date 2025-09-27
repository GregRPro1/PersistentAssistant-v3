# tools/apply_simple_patches.py
# Purpose: apply tiny, explicit, JSON-defined text patches to files.
# Safe: makes timestamped .bak backups, literal (non-regex) replaces, supports "all" or "nth".
# Exit codes: 0=ok (>=1 patch applied), 2=no patches applied, 1=error.

from __future__ import annotations
import argparse, json, os, sys, time

def _backup_path(path: str) -> str:
    ts = time.strftime("%Y%m%d_%H%M%S")
    return f"{path}.bak.{ts}"

def _read_text(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def _write_text(path: str, text: str) -> None:
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text)

def _apply_one(patch: dict) -> bool:
    path = patch.get("path")
    find = patch.get("find")
    replace = patch.get("replace", "")
    all_flag = bool(patch.get("all", False))
    nth = patch.get("nth", None)  # 1-based index if provided

    if not path or not isinstance(path, str):
        print("[SKIP] invalid 'path' in patch")
        return False
    if not os.path.isfile(path):
        print(f"[MISS] {path} (file not found)")
        return False
    if find is None or not isinstance(find, str) or find == "":
        print(f"[SKIP] {path} (no valid 'find' provided)")
        return False

    original = _read_text(path)

    # Quick check
    occurrences = original.count(find)
    if occurrences == 0:
        print(f"[MISS] {path} (pattern not found)")
        return False

    new_text = original
    changed = False

    if all_flag:
        new_text = original.replace(find, replace)
        changed = (new_text != original)
    elif nth is not None:
        try:
            n = int(nth)
        except Exception:
            print(f"[SKIP] {path} (invalid nth='{nth}')")
            return False
        if n <= 0:
            print(f"[SKIP] {path} (nth must be 1-based)")
            return False
        # replace nth occurrence only
        idx = -1
        start = 0
        for _ in range(n):
            idx = new_text.find(find, start)
            if idx == -1:
                break
            start = idx + len(find)
        if idx == -1:
            print(f"[MISS] {path} (nth={n} not found)")
            return False
        new_text = new_text[:idx] + replace + new_text[idx+len(find):]
        changed = True
    else:
        # first occurrence only
        new_text = new_text.replace(find, replace, 1)
        changed = (new_text != original)

    if not changed:
        print(f"[NOOP] {path}")
        return False

    # Backup then write
    bkp = _backup_path(path)
    _write_text(bkp, original)
    _write_text(path, new_text)
    print(f"[OK]   {path} (backup: {bkp})")
    return True

def main() -> int:
    ap = argparse.ArgumentParser(description="Apply simple JSON patches (literal find/replace).")
    ap.add_argument("--patch", required=True, help="Path to JSON file: { 'patches': [ {path, find, replace, all?, nth?}, ... ] }")
    args = ap.parse_args()

    try:
        with open(args.patch, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"[ERR] failed to read JSON: {e}")
        return 1

    patches = data.get("patches", [])
    if not isinstance(patches, list) or not patches:
        print("No patches found.")
        return 2

    applied = 0
    for p in patches:
        try:
            if _apply_one(p):
                applied += 1
        except Exception as e:
            print(f"[ERR] patch failed for {p.get('path')}: {e}")

    print(f"Applied {applied}/{len(patches)} patches")
    if applied > 0:
        return 0
    # none applied (either misses or invalid) → 2
    return 2

if __name__ == "__main__":
    sys.exit(main())
