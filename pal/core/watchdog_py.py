
from __future__ import annotations
import logging, time
from pathlib import Path
from pal.core.ops import write_ops_snapshot, CFG_DEFAULT, read_yaml
from pal.core.tracker import start_tracker_if_needed

log = logging.getLogger("pal.watchdog")

class WatchdogLoop:
    def __init__(self, config_path: Path, interval: float = 5.0, ensure_tracker: bool = True, ensure_web: bool = True):
        self.config_path = config_path
        self.interval = interval
        self.ensure_tracker = ensure_tracker
        self.ensure_web = ensure_web
        self.reasons = []  # last N actions/decisions

    def _note(self, msg: str):
        log.info(msg)
        self.reasons.append(msg)
        if len(self.reasons) > 50:
            self.reasons = self.reasons[-50:]

    def iterate_once(self):
        cfg = CFG_DEFAULT.copy()
        cfg.update(read_yaml(self.config_path) or {})

        # ensure tracker
        if self.ensure_tracker:
            ok = start_tracker_if_needed()
            if ok: self._note("Tracker ensured (running)")

        # snapshot ops
        st = write_ops_snapshot(self.config_path)
        if not st.get("web", {}).get("port_ok"):
            self._note("Web port not listening; not starting a tunnel.")
        elif not st.get("web", {}).get("health_ok"):
            self._note("Web health check failed; not starting a tunnel.")
        else:
            self._note(f"Web healthy; ready for tunnel on port {st['web']['port']}.")

    def run_forever(self):
        while True:
            try:
                self.iterate_once()
            except Exception as e:
                log.exception("watchdog iteration error: %s", e)
            time.sleep(self.interval)
