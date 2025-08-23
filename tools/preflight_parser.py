# tools/preflight_parser.py
"""
Fail-soft Script Preflight Parser for Windows/PowerShell and common shells.
- Scans input script for risky patterns
- Emits warnings JSON
- Writes an auto-fixed script (non-blocking: inserts warnings/comments, safer forms)
- Creates a "fix-it" zip pack alongside report

Usage:
  python tools/preflight_parser.py --in foo.ps1 --out foo.safe.ps1 --report tmp/feedback/preflight_report.json
"""
from __future__ import annotations
import re, os, json, argparse, datetime, zipfile, hashlib, shutil, uuid

RISK_PATTERNS = [
    (r'\brm\s+-rf\b', 'Destructive recursive delete (rm -rf)'),
    (r'\brd\s+/s\s+/q\b', 'Destructive recursive delete (rd /s /q)'),
    (r'\bdel\s+/s\s+/q\b', 'Destructive recursive delete (del /s /q)'),
    (r'\bformat\s+\w', 'Disk format command'),
    (r'\bdiskpart\b', 'Disk partition manipulation'),
    (r'\bnetsh\s+advfirewall\s+set\s+allprofiles\s+state\s+off\b', 'Disable firewall'),
    (r'\biwr\s+[^|]+\|\s*iex\b', 'Downloaded script execution (iwr|iex)'),
    (r'\bInvoke-WebRequest\s+[^|]+\|\s*Invoke-Expression\b', 'Downloaded script execution (IWR|IEX)'),
    (r'\bSet-ExecutionPolicy\b', 'Execution policy change'),
    (r'\bbcdedit\b', 'Boot configuration modification'),
    (r'python\s+-\s+<<', 'Here-doc python (forbidden in brief)'),
]

def auto_fix(line: str) -> str:
    # Non-blocking "fixes": convert direct pipe-to-exec downloads into save-to-file steps + echo warning
    if re.search(r'\biwr\s+[^|]+\|\s*iex\b', line, flags=re.I) or re.search(r'Invoke-WebRequest\s+[^|]+\|\s*Invoke-Expression\b', line, flags=re.I):
        m = re.search(r'(iwr|Invoke-WebRequest)\s+([^\s|]+)', line, flags=re.I)
        url = m.group(2) if m else "<URL>"
        tmp = f"$env:TEMP\\payload_{uuid.uuid4().hex}.ps1"
        fixed = [
            f'Write-Host "[WARN][Preflight] Remote code execution detected. Downloading to {tmp} instead of piping to IEX."',
            f'Invoke-WebRequest -UseBasicParsing -Uri "{url}" -OutFile "{tmp}"',
            'Write-Host "[WARN][Preflight] Review downloaded file before execution."',
            f'# Start-Process powershell -Verb RunAs -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File \\"{tmp}\\""',
        ]
        return "\n".join(fixed)
    # Strip here-doc python
    if re.search(r'python\s+-\s+<<', line, flags=re.I):
        return 'Write-Host "[WARN][Preflight] Here-doc python suppressed per brief (no heredocs)."\n# original removed'
    return line

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--out", dest="out", required=True)
    ap.add_argument("--report", dest="report", required=True)
    args = ap.parse_args()

    with open(args.inp, "r", encoding="utf-8", errors="replace") as f:
        src = f.read()

    warnings = []
    fixed_lines = []
    for ln in src.splitlines():
        ln_fixed = ln
        for pat, msg in RISK_PATTERNS:
            if re.search(pat, ln, flags=re.I):
                warnings.append({"pattern": pat, "msg": msg, "line": ln.strip()})
                ln_fixed = auto_fix(ln_fixed)
        fixed_lines.append(ln_fixed)

    fixed = "\n".join(fixed_lines)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(fixed)

    os.makedirs(os.path.dirname(args.report), exist_ok=True)
    rep = {
        "generated": datetime.datetime.utcnow().isoformat()+"Z",
        "input": args.inp,
        "output": args.out,
        "warnings": warnings,
        "counts": {"warnings": len(warnings)},
    }
    with open(args.report, "w", encoding="utf-8") as f:
        json.dump(rep, f, indent=2)

    # Fix-it pack zip
    base = os.path.splitext(os.path.basename(args.out))[0]
    pack_dir = os.path.join("tmp","feedback")
    os.makedirs(pack_dir, exist_ok=True)
    pack_path = os.path.join(pack_dir, f"pack_fixit_{base}.zip")
    with zipfile.ZipFile(pack_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("README_fixit.txt", "Auto-fixed script produced by preflight parser. Review warnings in report JSON.")
        z.write(args.out, arcname=os.path.basename(args.out))
        z.write(args.report, arcname=os.path.basename(args.report))

    print(pack_path)

if __name__ == "__main__":
    main()
