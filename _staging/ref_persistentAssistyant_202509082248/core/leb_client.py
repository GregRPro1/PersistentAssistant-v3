# core/leb_client.py
# Minimal HTTP client for Local Exec Bridge (LEB)
import json, time
from dataclasses import dataclass
from typing import Any, Dict, Optional
import requests

@dataclass
class LEBClient:
    host: str = "127.0.0.1"
    port: int = 8765
    timeout: float = 20.0

    @property
    def base(self) -> str:
        return f"http://{self.host}:{self.port}"

    def ping(self) -> Dict[str, Any]:
        r = requests.get(self.base + "/ping", timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def run(self, cmd: str) -> Dict[str, Any]:
        r = requests.post(self.base + "/run", json={"cmd": cmd}, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def logs(self) -> Dict[str, Any]:
        r = requests.get(self.base + "/logs", timeout=self.timeout)
        r.raise_for_status()
        return r.json()
