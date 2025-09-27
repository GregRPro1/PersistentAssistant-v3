import hashlib, os, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
JS = ROOT / "web" / "pwa" / "settings_ext.js"

def sha256(p: Path) -> str:
    import hashlib
    return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    if not JS.exists():
        print("status: ERROR"); print("reason: not found:", JS); sys.exit(1)

    before = JS.read_text(encoding="utf-8", errors="replace")
    h_before = sha256(JS)
    src = before
    changed = False
    notes = []

    # A) Remove any wireApplyButton(...) call (prevents double handlers)
    pat_call = r"""^\s*wireApplyButton\(\s*btnApply\s*,\s*out\s*,\s*\(\)\s*=>\s*selectedStep\s*\)\s*;[ \t]*$"""
    new_src = re.sub(pat_call, "", src, flags=re.MULTILINE)
    if new_src != src:
        src = new_src; changed = True
        notes.append("- removed: wireApplyButton(...) call")

    # B) Remove all existing btnApply click listeners, then add one canonical listener
    rm_listeners = re.compile(r"""btnApply\.addEventListener\(\s*(['"])click\1\s*,\s*[^)]+\)\s*;""", re.MULTILINE)
    if rm_listeners.search(src):
        src = rm_listeners.sub("", src)
        changed = True
        notes.append("- removed: existing btnApply 'click' listeners")

    anchor = r"""controls\.append\(btnRefresh,\s*btnAccept,\s*btnApply,\s*btnApprove\)\s*;\s*card\.append"""
    inject = "btnApply.addEventListener('click', applyStep, { passive: true });\n    "
    src2, n = re.subn(anchor, inject + r"\g<0>", src)
    if n > 0 and src2 != src:
        src = src2; changed = True
        notes.append("- added: canonical btnApply listener via anchor")
    else:
        fb = r"""const\s+btnApply\s*=\s*el\(\s*['"]button['"]\s*,\s*['"]btn['"]\s*,\s*['"]Apply step \(run driver\)['"]\s*\)\s*;"""
        src2, n2 = re.subn(fb, r"\g<0>\n    " + inject, src)
        if n2 > 0 and src2 != src:
            src = src2; changed = True
            notes.append("- added: canonical listener after btnApply declaration")

    if not changed:
        print("status: NOOP"); print("sha256:", h_before); return

    # backup + write
    backup = JS.with_suffix(".js.bak_applycleanup")
    i = 0
    while backup.exists():
        i += 1
        backup = JS.with_name(f"{JS.name}.bak_applycleanup_{i}")
    backup.write_text(before, encoding="utf-8")
    JS.write_text(src, encoding="utf-8")

    h_after = sha256(JS)
    print("status: UPDATED")
    print("backup:", backup.name)
    print("sha256_before:", h_before)
    print("sha256_after :", h_after)
    for n in notes: print(n)

if __name__ == "__main__":
    main()
