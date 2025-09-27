# tools/py/repair_server_syntax.py
# Cleans control chars, fixes known bad escapes in micro_approvals.py, compiles all server/*.py, and reports wrapper import status.

import argparse, os, sys, json, time, unicodedata, py_compile, traceback, importlib

ALLOW = {"\n", "\r", "\t"}

def strip_nonprintable(text: str) -> str:
    out = []
    for ch in text:
        if ch in ALLOW:
            out.append(ch)
            continue
        cat = unicodedata.category(ch)  # e.g. 'Cc' control char
        if cat and cat.startswith("C"):
            # drop non-printable/control
            continue
        out.append(ch)
    return "".join(out)

def fix_micro_approvals(text: str) -> str:
    # Known bad: val.startswith("\\"") / val.endswith("\\"")
    text = text.replace('val.startswith("\\"")', 'val.startswith(\'"\')')
    text = text.replace('val.endswith("\\"")', 'val.endswith(\'"\')')
    return text

def process_file(path: str) -> dict:
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        orig = f.read()
    cleaned = strip_nonprintable(orig)
    base = os.path.basename(path)
    if base == "micro_approvals.py":
        cleaned = fix_micro_approvals(cleaned)
    changed = (cleaned != orig)
    if changed:
        bkp = f"{path}.bak.{time.strftime('%Y%m%d_%H%M%S')}"
        with open(bkp, "w", encoding="utf-8") as f:
            f.write(orig)
        with open(path, "w", encoding="utf-8") as f:
            f.write(cleaned)

    ok, err = True, ""
    try:
        py_compile.compile(path, doraise=True)
    except Exception as e:
        ok = False
        err = "".join(traceback.format_exception_only(type(e), e)).strip()
    return {"file": path, "changed": changed, "ok": ok, "err": err}

def import_wrapper() -> dict:
    info = {"ok": True, "trace": "", "has_app": False, "file": None}
    try:
        m = importlib.import_module("server.agent_sidecar_wrapper")
        info["file"] = getattr(m, "__file__", None)
        app = getattr(m, "app", None)
        info["has_app"] = bool(app)
    except Exception:
        info["ok"] = False
        info["trace"] = traceback.format_exc()
    return info

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--out", default="tmp/run/repair_server_syntax.json")
    args = ap.parse_args()

    root = os.path.abspath(args.root)
    server = os.path.join(root, "server")

    results = []
    for base, _, files in os.walk(server):
        for fn in files:
            if fn.endswith(".py"):
                results.append(process_file(os.path.join(base, fn)))

    wrap = import_wrapper()
    out = {"results": results, "wrapper": wrap}
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)

    bad = [r for r in results if not r["ok"]]
    print(f"Repaired {sum(1 for r in results if r['changed'])} files; "
          f"compile errors: {len(bad)}; wrapper_import_ok={wrap['ok']} has_app={wrap['has_app']}")

if __name__ == "__main__":
    main()
