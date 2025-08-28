# tools/py/auto_fix_main_if_block.py
# Idempotently inserts `pass` under a bare `if __name__ == "__main__":` that has no indented body.
# Usage: python tools\py\auto_fix_main_if_block.py --file server\agent_sidecar_wrapper.py

import argparse, os, sys, time

def backup(path, text):
    ts = time.strftime("%Y%m%d_%H%M%S")
    bkp = f"{path}.bak.{ts}"
    with open(bkp, "w", encoding="utf-8") as f:
        f.write(text)
    return bkp

def needs_pass(lines, i):
    # i points to the if-line
    this = lines[i]
    indent = len(this) - len(this.lstrip(" "))
    # find first non-empty, non-comment line after i
    j = i + 1
    while j < len(lines) and lines[j].strip() == "":
        j += 1
    if j >= len(lines):
        # EOF -> no body
        return True, indent, j
    nxt = lines[j]
    nxt_indent = len(nxt) - len(nxt.lstrip(" "))
    # If next significant line is NOT more indented, the 'if' has no body
    return nxt_indent <= indent, indent, j

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True)
    args = ap.parse_args()

    path = args.file
    if not os.path.isfile(path):
        print(f"[MISS] {path} not found")
        sys.exit(1)

    with open(path, "r", encoding="utf-8", errors="replace") as f:
        text = f.read()
    lines = text.splitlines(True)

    changed = False
    for i, line in enumerate(lines):
        s = line.strip()
        if s.startswith('if __name__ == "__main__":') or s.startswith("if __name__ == '__main__':"):
            needed, indent, insert_at = needs_pass(lines, i)
            if needed:
                bkp = backup(path, text)
                pad = " " * (indent + 4)
                lines.insert(insert_at, pad + "pass\n")
                with open(path, "w", encoding="utf-8") as f:
                    f.write("".join(lines))
                print(f"[OK]   inserted pass under __main__ if (backup: {bkp})")
                changed = True
            else:
                print("[NOOP] __main__ if already has a body")
            break

    if not changed:
        print("[NOOP] no bare __main__ if found or no change needed")
    sys.exit(0)

if __name__ == "__main__":
    main()
