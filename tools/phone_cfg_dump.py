from __future__ import annotations
import json, pathlib
import yaml
CFG = pathlib.Path("config/phone/phone.yaml")
if not CFG.exists():
    CFG.parent.mkdir(parents=True, exist_ok=True)
    CFG.write_text('token: "CHANGE_ME"\nallow_cidr: "192.168.1.0/24"\nhost: "0.0.0.0"\nport: 8770\n', encoding="utf-8")
d = yaml.safe_load(CFG.read_text(encoding="utf-8")) or {}
print(json.dumps({
    "token": d.get("token") or "CHANGE_ME",
    "allow_cidr": d.get("allow_cidr") or "192.168.1.0/24",
    "host": d.get("host") or "0.0.0.0",
    "port": int(d.get("port") or 8770),
}))
