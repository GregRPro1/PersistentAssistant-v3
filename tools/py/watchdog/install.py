from __future__ import annotations
import argparse, pathlib, subprocess, sys, shutil, json, os
from typing import Any, Dict

ROOT = pathlib.Path(__file__).resolve().parents[2]
WDIR = ROOT / "tools" / "py" / "watchdog"
CFG  = ROOT / "config" / "pa_watchdog.yaml"

TEMPLATE = lambda host,port,email,phone: "\n".join([
    "agent:",
    f"  host: \"{host}\"",
    f"  port: {port}",
    "  health_path: \"/health\"",
    "  start_timeout_sec: 25",
    "  start_command: \"python tools/py/pa_agent_bringup.py --host {host} --port {port} --timeout 25\"",
    "policy:",
    "  heartbeat_every_sec: 120",
    "  max_restarts_per_hour: 3",
    "  give_up_min_backoff_sec: 900",
    "notify:",
    "  email:",
    "    enabled: true",
    f"    to: \"{email}\"",
    "    smtp_host: \"\"",
    "    smtp_port: 587",
    "    username: \"\"",
    "    password_env: \"PA_SMTP_PASS\"",
    "    from: \"pa-watchdog@localhost\"",
    "  slack_webhook:",
    "    enabled: false",
    "    url: \"\"",
    "  whatsapp:",
    "    enabled: false",
    "    provider: \"twilio\"",
    "    from: \"\"",
    f"    to: \"{phone}\"",
    "    account_sid_env: \"TWILIO_SID\"",
    "    auth_token_env: \"TWILIO_TOKEN\"",
])

def write_cfg(host: str, port: int, email: str, phone: str) -> None:
    CFG.parent.mkdir(parents=True, exist_ok=True)
    if not CFG.exists():
        CFG.write_text(TEMPLATE(host, port, email, phone), encoding="utf-8")

def schtasks_create(minutes: int) -> Dict[str, Any]:
    # Runs watchdog every N minutes as SYSTEM
    exe = shutil.which("python") or sys.executable
    task_name = r"\PA\PA_Watchdog"
    cmd = f"\"{exe}\" \"{(WDIR / 'watchdog.py').as_posix()}\" --config \"{CFG.as_posix()}\""
    # Delete then create for idempotency
    subprocess.run(["schtasks", "/Delete", "/F", "/TN", task_name], capture_output=True)
    r = subprocess.run([
        "schtasks","/Create","/F",
        "/SC","MINUTE","/MO", str(minutes),
        "/RL","LIMITED",
        "/TN", task_name,
        "/TR", cmd,
        "/RU","SYSTEM"
    ], capture_output=True, text=True, encoding="utf-8", errors="replace")
    return {"rc": r.returncode, "out": r.stdout, "err": r.stderr, "task": task_name, "cmd": cmd}

def schtasks_delete() -> Dict[str, Any]:
    task_name = r"\PA\PA_Watchdog"
    r = subprocess.run(["schtasks","/Delete","/F","/TN",task_name], capture_output=True, text=True, encoding="utf-8", errors="replace")
    return {"rc": r.returncode, "out": r.stdout, "err": r.stderr}

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8782)
    ap.add_argument("--minutes", type=int, default=2)
    ap.add_argument("--email", default="")
    ap.add_argument("--phone", default="")
    ap.add_argument("--uninstall", action="store_true")
    args = ap.parse_args()

    if args.uninstall:
        res = schtasks_delete()
        print(json.dumps({"action":"uninstall","result":res}, indent=2))
        return 0

    write_cfg(args.host, args.port, args.email, args.phone)
    res = schtasks_create(args.minutes)
    print(json.dumps({"action":"install","result":res}, indent=2))
    return 0

if __name__ == "__main__":
    sys.exit(main())
