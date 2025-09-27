# tools/py/pa_agent_bringup.py
# Start server/agent_sidecar_wrapper.py, write logs, and probe /health + /__routes__.
# Pure Python; no PS dependencies; robust and quiet.

from __future__ import annotations
import os, sys, time, json, subprocess, pathlib, urllib.request, urllib.error, argparse, socket
import subprocess, re, time  # ensure these are imported

ROOT = pathlib.Path(__file__).resolve().parents[2]
TMP   = ROOT / "tmp"
LOGS  = TMP / "logs"
RUN   = TMP / "run"
SRV   = ROOT / "server" / "agent_sidecar_wrapper.py"

def _netstat_pids_listening_on(port: int):
    try:
        cp = subprocess.run(["netstat","-ano"], capture_output=True, text=True, shell=False)
        if cp.returncode != 0:
            return set()
        pat = re.compile(rf":{port}\b")
        pids = set()
        for ln in cp.stdout.splitlines():
            if "LISTENING" in ln and pat.search(ln):
                parts = ln.split()
                if parts and parts[-1].isdigit():
                    pids.add(int(parts[-1]))
        return pids
    except Exception:
        return set()

def _kill_port_windows(port: int) -> list[tuple[int,int,str]]:
    out = []
    pids = sorted(_netstat_pids_listening_on(port))
    for pid in pids:
        cp = subprocess.run(["taskkill","/PID",str(pid),"/F"], capture_output=True, text=True, shell=False)
        msg = cp.stdout.strip() or cp.stderr.strip()
        out.append((pid, cp.returncode, msg))
    time.sleep(0.8)
    return out


def ensure_dirs():
    for p in (TMP, LOGS, RUN): p.mkdir(parents=True, exist_ok=True)

def port_free(host:str, port:int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.3)
        return s.connect_ex((host, port)) != 0

def http_get(url:str, timeout:float=3.0) -> tuple[int,str,str]:
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as r:
            ct = r.headers.get("Content-Type","")
            body = r.read().decode("utf-8","replace")
            return (r.getcode(), ct, body)
    except urllib.error.HTTPError as e:
        try: body = e.read().decode("utf-8","replace")
        except Exception: body = str(e)
        return (e.code or 0, "", body)
    except Exception as e:
        return (0, "", f"{type(e).__name__}: {e}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8782)
    ap.add_argument("--timeout", type=int, default=25)
    ap.add_argument("--force-kill", action="store_true", help="If port is busy, kill listeners and continue")

    args = ap.parse_args()

    ensure_dirs()

    if not SRV.exists():
        print(f"FAIL: missing {SRV}")
        return 2

    host = args.host
    port = args.port
    if not port_free(host, port):
        if args.force_kill:
            print(f"[INFO] Port {host}:{port} busy; attempting to free it...")
            results = _kill_port_windows(port)
            for pid, rc, msg in results:
                print(f"[KILL] pid={pid} rc={rc} msg={msg}")
            # re-check
            if _netstat_pids_listening_on(port):
                print(f"FAIL: {host}:{port} still in use after --force-kill.")
                return 2
            else:
                print(f"[OK] Freed {host}:{port}; continuing bring-up.")
                # fall through to normal start/probe
        else:
            print(f"FAIL: {host}:{port} already in use; pick another port or stop the listener.")
            return 2

    ts = time.strftime("%Y%m%d_%H%M%S")
    out_log = LOGS / f"sidecar_{args.port}_{ts}.out.log"
    err_log = LOGS / f"sidecar_{args.port}_{ts}.err.log"

    env = os.environ.copy()
    env["PA_SIDECAR_HOST"] = args.host
    env["PA_SIDECAR_PORT"] = str(args.port)

    # Start the wrapper
    with open(out_log, "w", encoding="utf-8") as out, open(err_log, "w", encoding="utf-8") as err:
        proc = subprocess.Popen(
            [sys.executable, str(SRV)],
            cwd=str(ROOT),
            stdout=out,
            stderr=err,
            env=env
        )

    health = f"http://{args.host}:{args.port}/health"
    routes = f"http://{args.host}:{args.port}/__routes__"

    # Poll for readiness
    deadline = time.time() + args.timeout
    up = False
    while time.time() < deadline:
        code, _, _ = http_get(health, timeout=1.5)
        if 200 <= code < 300:
            up = True
            break
        time.sleep(0.4)

    if not up:
        print(f"FAIL: agent did not respond at {health} within {args.timeout}s")
        # print tails to console
        try:
            print("---- sidecar.err tail ----")
            print((err_log.read_text(encoding="utf-8", errors="replace"))[-4000:])
        except Exception: pass
        try:
            print("---- sidecar.out tail ----")
            print((out_log.read_text(encoding="utf-8", errors="replace"))[-2000:])
        except Exception: pass
        print(f"LOGS: {out_log} | {err_log}")
        return 4

    # Probe routes
    h_code, _, h_body = http_get(health, timeout=2.5)
    r_code, _, r_body = http_get(routes, timeout=3.0)

    print(f"OK: {health} code={h_code}")
    # try to count agent_* endpoints if JSON
    agent_count = None
    try:
        obj = json.loads(r_body)
        rs = obj.get("routes") or []
        agent_count = sum(1 for r in rs if "agent" in (r.get("rule","")))
    except Exception:
        pass
    if agent_count is not None:
        print(f"ROUTES: {r_code} with ~{agent_count} agent* rules")
    else:
        print(f"ROUTES: {r_code}")

    print(f"LOGS: {out_log} | {err_log}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
