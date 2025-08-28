from __future__ import annotations
import argparse, time, json, pathlib
from typing import Dict, Any, List
from .config import ensure_dirs, load_config, load_state, save_state, ROOT, WD
from .notify import send_notifications
from .agent import http_get, start_and_wait

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=str(ROOT / "config" / "pa_watchdog.yaml"))
    args = ap.parse_args()

    ensure_dirs()
    cfg = load_config(pathlib.Path(args.config))
    agent = cfg["agent"]
    url = f"http://{agent.get('host','127.0.0.1')}:{agent.get('port',8782)}{agent.get('health_path','/health')}"
    st = load_state()
    now = int(time.time())

    # give-up window
    if now < int(st.get("give_up_until", 0)):
        _write_heartbeat(ok=False, url=url, msg="give_up_window")
        return 0

    code, _ = http_get(url, timeout=2.0)
    if 200 <= code < 300:
        st["last_ok"] = now
        save_state(st)
        _write_heartbeat(ok=True, url=url, msg="ok")
        return 0

    # not healthy -> restart
    start_cmd = str(agent.get("start_command", "")).replace("{host}", str(agent.get("host"))).replace("{port}", str(agent.get("port")))
    ok = start_and_wait(start_cmd, agent.get("host","127.0.0.1"), int(agent.get("port",8782)),
                        agent.get("health_path","/health"), int(agent.get("start_timeout_sec",25)))
    # update restart history
    st = load_state()
    lst: List[int] = list(map(int, st.get("restart_ts", [])))
    lst = [t for t in lst if t >= now - 3600]
    lst.append(now)
    st["restart_ts"] = lst
    save_state(st)

    if not ok:
        _write_heartbeat(ok=False, url=url, msg="restart_failed")

    max_per_hr = int(cfg.get("policy",{}).get("max_restarts_per_hour", 3))
    if len(lst) > max_per_hr:
        st["give_up_until"] = now + int(cfg.get("policy",{}).get("give_up_min_backoff_sec", 900))
        save_state(st)
        send_notifications(cfg, "PA Watchdog: giving up", f"Too many restarts in last hour: {len(lst)}")
        return 2
    return 0

def _write_heartbeat(ok: bool, url: str, msg: str) -> None:
    try:
        WD.mkdir(parents=True, exist_ok=True)
        hb = {"ok": ok, "ts": int(time.time()), "url": url, "msg": msg}
        with open(WD / "heartbeat.json", "w", encoding="utf-8") as f:
            json.dump(hb, f)
    except Exception:
        pass

if __name__ == "__main__":
    import sys
    sys.exit(main())
