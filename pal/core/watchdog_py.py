
from __future__ import annotations
import json, time, logging, subprocess, sys, os
from pathlib import Path
from typing import Optional, Dict, Any
from pal.core.ops import write_ops_snapshot, ensure_dirs, CFG_DEFAULT, read_yaml

log = logging.getLogger("pal.watchdog")

class WatchdogLoop:
    def __init__(self, config_path: Path, interval: float = 5.0, ensure_tracker: bool = True, ensure_web: bool = True):
        self.config_path = config_path
        self.interval = interval
        self.ensure_tracker = ensure_tracker
        self.ensure_web = ensure_web

    def _start_process(self, args: list[str], name: str) -> None:
        try:
            subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            log.info("started %s: %s", name, " ".join(args))
        except Exception as e:
            log.warning("failed to start %s: %s", name, e)

    def _ensure_web_placeholder(self):
        # optional minimal placeholder server under current/server.py if present
        server = Path("current/server.py")
        if not server.exists(): return
        # check if something bound (ops check will catch) else start python server
        # naive: rely on ops snapshot tcp check; here just attempt once per run
        pass

    def run_forever(self):
        ensure_dirs()
        cfg = CFG_DEFAULT.copy()
        cfg.update(read_yaml(self.config_path) or {})
        while True:
            try:
                write_ops_snapshot(self.config_path)
                if self.ensure_tracker:
                    from pal.core.tracker import start_tracker_if_needed
                    start_tracker_if_needed()
                if self.ensure_web:
                    self._ensure_web_placeholder()
            except Exception as e:
                log.exception("watchdog iteration error: %s", e)
            time.sleep(self.interval)
