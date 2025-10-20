Phone Bridge + Cloudflared Quick Tunnel

Apply:
  python .\scripts\apply_pack.py -ZipPath "$env:USERPROFILE\Downloads\PAL20251019K_phone_bridge_remote_pack.zip"

Run bridge:
  python .\scripts\phone\phone_bridge.py
Phone UI:
  http://127.0.0.1:5080/app

Remote (requires cloudflared.exe in PATH):
  powershell -ExecutionPolicy Bypass -File .\scripts\tunnel\run_cloudflared_quick.ps1
  # -> see URL in reports\tunnel\public_url.txt

Smokes:
  powershell -ExecutionPolicy Bypass -File .\scripts\smoke\smoke_phone_bridge.ps1
  powershell -ExecutionPolicy Bypass -File .\scripts\smoke\smoke_tunnel.ps1

Optional Supervisor children:
  "phonesvc": ["python", "scripts/phone/phone_bridge.py"]
  "tunnelsvc": ["powershell","-ExecutionPolicy","Bypass","-File","scripts/tunnel/run_cloudflared_quick.ps1"]
