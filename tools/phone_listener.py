from __future__ import annotations
import os, time, json, pathlib, datetime, subprocess, sys
ROOT = pathlib.Path(__file__).resolve().parents[1]
APPROVE_DIR = ROOT / "tmp" / "phone" / "approvals"
LOG = ROOT / "tmp" / "logs" / "phone_listener.log"
def log(msg: str):
    ts = datetime.datetime.utcnow().isoformat()+"Z"
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(f"[{ts}] {msg}\n")
    print(msg)
def run_cmd(cmd):
    try:
        p = subprocess.run(cmd, capture_output=True, text=True)
        log(f"RUN {cmd!r} rc={p.returncode}")
        if p.stdout: log("stdout: " + p.stdout.strip().replace("\n"," | "))
        if p.stderr: log("stderr: " + p.stderr.strip().replace("\n"," | "))
        return p.returncode
    except Exception as e:
        log(f"ERR running {cmd!r}: {e}")
        return 1
def handle(action: str) -> int:
    if action in ("NEXT","RUN_NEXT"):
        rc = run_cmd([sys.executable, "tools/export_insights.py"])
        rc2 = run_cmd([sys.executable, "tools/apply_and_pack.py"])
        return rc or rc2
    elif action.startswith("RUN:"):
        return run_cmd([sys.executable] + action[4:].strip().split())
    else:
        log(f"UNKNOWN action: {action}")
        return 2
def main():
    APPPROVED = set()
    APPROVE_DIR.mkdir(parents=True, exist_ok=True)
    log("Listener started; watching approvals...")
    while True:
        for p in sorted(APPROVE_DIR.glob("approve_*.json")):
            key = str(p)
            if key in APPPROVED: 
                continue
            try:
                d = json.loads(p.read_text(encoding="utf-8"))
            except Exception as e:
                log(f"Bad JSON {p.name}: {e}"); APPPROVED.add(key); continue
            ts = d.get("ts")
            if ts:
                try:
                    t = datetime.datetime.fromisoformat(ts.replace("Z","+00:00"))
                    age = (datetime.datetime.now(datetime.timezone.utc) - t).total_seconds()
                    if age > 120:
                        log(f"REJECT stale approval ({age:.1f}s): {p.name}")
                        APPPROVED.add(key); continue
                except Exception:
                    pass
            action = (d.get("action") or "").strip().upper()
            rc = handle(action)
            log(f"Handled {p.name} action={action} rc={rc}")
            APPPROVED.add(key)
        time.sleep(1.0)
if __name__ == "__main__":
    raise SystemExit(main())
