# tools/py/lint/reply_lint.py
# Purpose: scan text files for banned shell constructs (POSIX heredocs, PowerShell here-strings, etc.).
# Exit codes: 0=OK, 2=violations found, 3=IO/usage error.
from __future__ import annotations
import argparse, re, sys, json
from pathlib import Path

BANNED_PATTERNS = {
    # POSIX heredocs (generic), explicit python heredoc
    r"<<\s*[\"']?EOF[\"']?": "posix_heredoc_EOF",
    r"<<\s*[\"']?[A-Za-z_][A-Za-z0-9_]*[\"']?": "posix_heredoc_named",
    r"python\s+-\s*<<": "python_stdin_heredoc",
    r"<<<": "posix_triple_chevron",
    # PowerShell here-strings (both types)
    r"@\"": "pwsh_here_string_start_double",
    r"@'": "pwsh_here_string_start_single",
    r"\"@": "pwsh_here_string_end_double",
    r"'@": "pwsh_here_string_end_single",
}

def scan_file(path: Path) -> list[dict]:
    try:
        txt = path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return [{"file": str(path), "error": f"read_error: {e}"}]
    issues = []
    # line-based for line numbers + multi-line sweep for here-strings
    lines = txt.splitlines()
    for i, line in enumerate(lines, 1):
        for pat, tag in BANNED_PATTERNS.items():
            if re.search(pat, line):
                issues.append({"file": str(path), "line": i, "pattern": pat, "tag": tag, "text": line.strip()})
    return issues

def main():
    ap = argparse.ArgumentParser(description="Lint text for banned constructs.")
    ap.add_argument("--path", action="append", help="File to check (repeatable).")
    ap.add_argument("--glob", action="append", help="Globs to expand (repeatable).")
    ap.add_argument("--json-out", help="Write JSON report to this path.")
    args = ap.parse_args()

    if not args.path and not args.glob:
        print("usage error: provide --path and/or --glob", file=sys.stderr)
        return 3

    files: set[Path] = set()
    if args.path:
        for p in args.path:
            files.add(Path(p))
    if args.glob:
        for g in args.glob:
            for p in Path(".").glob(g):
                if p.is_file():
                    files.add(p)

    all_issues: list[dict] = []
    for f in sorted(files):
        all_issues.extend(scan_file(f))

    if args.json_out:
        Path(args.json_out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json_out).write_text(json.dumps({"issues": all_issues}, indent=2), encoding="utf-8")

    if all_issues:
        for it in all_issues:
            if "error" in it:
                print(f"[READ-ERR] {it['file']}: {it['error']}")
            else:
                print(f"[BANNED] {it['file']}:{it['line']} {it['tag']} :: {it['text']}")
        print(f"SUMMARY: {len(all_issues)} issue(s) across {len({i['file'] for i in all_issues})} file(s)")
        return 2

    print("Reply lint: OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
