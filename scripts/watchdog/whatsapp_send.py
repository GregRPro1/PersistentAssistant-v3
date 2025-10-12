#!/usr/bin/env python3
# Optional CLI sender for Meta WhatsApp Cloud API if configured.
import sys, json, urllib.request
from pathlib import Path

CFG = Path(r"C:\_Repos\PersistentAssistant\config\pal_settings.yaml")
def load_yaml_map(path: Path):
    data = {}; cur=None
    if not path.exists(): return {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.strip().startswith("#"): continue
        if not line.startswith(" "):
            if ":" in line: cur=line.split(":",1)[0].strip(); data[cur]={}
        else:
            if ":" in line and cur is not None:
                k,v=line.strip().split(":",1); data[cur][k.strip()]=v.strip().strip('"').strip("'")
    return data

S = load_yaml_map(CFG).get("whatsapp",{})
if str(S.get("cloud_api_enabled","false")).lower()!="true":
    print("Cloud API not enabled"); sys.exit(2)
token=S.get("cloud_access_token",""); phone=S.get("cloud_phone_number_id",""); to=S.get("cloud_to_number","")
if not (token and phone and to): print("Missing token/phone_id/to"); sys.exit(2)
msg = sys.argv[1] if len(sys.argv)>1 else "Hello from PAL"
req = urllib.request.Request(
    f"https://graph.facebook.com/v19.0/{phone}/messages",
    method="POST",
    headers={"Authorization": f"Bearer {token}","Content-Type":"application/json"},
    data=json.dumps({"messaging_product":"whatsapp","to":to,"type":"text","text":{"body":msg}}).encode("utf-8")
)
with urllib.request.urlopen(req, timeout=8) as r:
    print("Sent:", r.status)
