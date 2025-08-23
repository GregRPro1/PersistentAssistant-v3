from __future__ import annotations
import sys, os, subprocess, shlex, time, json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOG  = ROOT / "data" / "insights" / "errors.log"
CAPTURE_YAML = ROOT / "data" / "insights" / "capture_errors.yaml"
CAPTURE_LAST = ROOT / "data" / "insights" / "capture_last.json"

def now() -> str:
    return datetime.now(timezone.utc).isoformat()

def ensure_parent(p: Path) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)

def exe() -> str:
    return sys.executable or "python"

def parse_cmd(argv: list[str]) -> list[str]:
    # Supported:
    #  - run_with_capture.py -- <args...>
    #  - run_with_capture.py '["python","tools/x.py"]'
    #  - run_with_capture.py "python tools/x.py"
    #  - run_with_capture.py python tools/x.py
    if not argv:
        raise SystemExit("usage: python tools/run_with_capture.py <command> or -- <args...>")
    if argv[0] == "--":
        cmd = argv[1:]
    elif len(argv) > 1:
        cmd = argv
    else:
        arg = argv[0]
        try:
            if arg.strip().startswith("["):
                cmd = json.loads(arg)
            else:
                cmd = shlex.split(arg)
        except Exception:
            cmd = arg.split(" ")  # last-resort fallback
    if cmd and cmd[0].lower() in ("python","py"):
        cmd[0] = exe()
    return cmd

def append_capture_record(record: dict) -> None:
    import yaml
    ensure_parent(CAPTURE_YAML)
    try:
        data = []
        if CAPTURE_YAML.exists():
            data = yaml.safe_load(CAPTURE_YAML.read_text(encoding="utf-8")) or []
            if not isinstance(data, list): data = []
        data.append(record)
        CAPTURE_YAML.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    except Exception:
        CAPTURE_YAML.with_suffix(".json").write_text(json.dumps(record, indent=2), encoding="utf-8")

def main():
    os.chdir(str(ROOT))
    if len(sys.argv) < 2:
        print("usage: python tools/run_with_capture.py <command> or -- <args...>")
        sys.exit(2)
    try:
        cmd = parse_cmd(sys.argv[1:])
    except SystemExit as e:
        print(str(e)); sys.exit(2)
    except Exception as e:
        rec = {"ts": now(), "phase": "parse_cmd", "error": f"{type(e).__name__}: {e}", "argv": sys.argv[1:]}
        append_capture_record(rec)
        ensure_parent(LOG)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(f"=== RUN @ {now()} ===\ncmd: (parse failed)\nexit: 2\n--- stderr ---\n{rec['error']}\n=== END ===\n\n")
        print(rec["error"], file=sys.stderr)
        sys.exit(2)

    t0 = time.time()
    p = subprocess.run(cmd, capture_output=True, text=True)
    dt = time.time() - t0

    ensure_parent(CAPTURE_LAST)
    CAPTURE_LAST.write_text(json.dumps({
        "ts": now(), "cmd": cmd, "exit": p.returncode,
        "elapsed_s": dt, "stdout": p.stdout, "stderr": p.stderr
    }, indent=2), encoding="utf-8")

    ensure_parent(LOG)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(f"=== RUN @ {now()} ===\n")
        f.write("cmd: " + " ".join(cmd) + "\n")
        f.write(f"exit: {p.returncode}, elapsed_s: {dt:.3f}\n")
        if p.stdout:
            f.write("--- stdout ---\n"); f.write(p.stdout)
            if not p.stdout.endswith("\n"): f.write("\n")
        if p.stderr:
            f.write("--- stderr ---\n"); f.write(p.stderr)
            if not p.stderr.endswith("\n"): f.write("\n")
        f.write("=== END ===\n\n")

    if p.returncode != 0:
        append_capture_record({
            "ts": now(),
            "phase": "subprocess",
            "cmd": cmd,
            "exit": p.returncode,
            "elapsed_s": dt,
            "stderr": p.stderr,
        })

    if p.stdout: print(p.stdout, end="")
    if p.stderr: print(p.stderr, end="", file=sys.stderr)
    sys.exit(p.returncode)

if __name__ == "__main__":
    main()
