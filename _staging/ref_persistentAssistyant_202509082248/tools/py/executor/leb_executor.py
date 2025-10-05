from __future__ import annotations
import json
from typing import Any, Dict

DEFAULT_BASE = "http://127.0.0.1:8765"

class LEBExecutor:
    def __init__(self, base: str = DEFAULT_BASE, timeout: float = 20.0):
        self.base = base.rstrip("/")
        self.timeout = timeout

    def _post_json(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.base}{path}"
        # Try requests first; fall back to urllib if not installed
        try:
            import requests  # type: ignore
            r = requests.post(url, json=payload, timeout=self.timeout)
            r.raise_for_status()
            return r.json()
        except Exception:
            import urllib.request, urllib.error
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read().decode("utf-8")
                return json.loads(raw)

    def run(self, cmd: str) -> Dict[str, Any]:
        if not isinstance(cmd, str) or not cmd.strip():
            return {"ok": False, "error": "empty_cmd"}
        return self._post_json("/run", {"cmd": cmd})

    def run_py(self, args: str) -> Dict[str, Any]:
        args = args.strip()
        if not args.startswith("python "):
            args = "python " + args
        return self.run(args)

    def run_pytest(self, tests: str, quiet: bool = True) -> Dict[str, Any]:
        t = tests.strip()
        if not t:
            return {"ok": False, "error": "empty_tests"}
        q = "-q " if quiet else ""
        return self.run(f"pytest {q}{t}")
