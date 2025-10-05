# Phone Approvals + Diagnostics + Preflight (7.5b, 7.5c, 7.7)

## 1) Copy pack into repo
- Place the contents under your repo so the relative paths match (`server/`, `web/pwa/`, `config/`, `tools/`). Or run:
  ```powershell
  .\tools\apply_pack_phone.ps1 -RepoRoot .
  ```

## 2) Configure token and allow-list
```powershell
.\tools\gen_phone_token.ps1 -UpdateConfig
# then edit config\phone_approvals.yaml if you want to change allow_cidrs or directories
```

## 3) Register Flask blueprints
In your Flask app init (where you build the main app for the dev server on :8770):
```python
from server.phone_blueprint import register_phone_blueprint
from server.logs_tail import logs_bp

app = register_phone_blueprint(app)
app.register_blueprint(logs_bp)
```
Ensure the dev server binds on 0.0.0.0:8770 so your phone can reach it on LAN.

## 4) Open the PWA
- Navigate on your phone to: `http://<YOUR_PC_LAN_IP>:8770/phone/pwa/index.html`
- Save the token in the UI (stored locally on device). Use the "One-tap Approval" button.
- Fallback files land in `tmp\phone\approvals\approve_*.json` (created by the server).

## 5) Preflight Parser (7.7)
Example:
```powershell
python tools\preflight_parser.py --in scripts\incoming.ps1 --out tmp\safe\incoming.safe.ps1 --report tmp\feedback\preflight_report.json
```
- Non-blocking: risky patterns are replaced with safer forms and warnings are injected as comments/echo; script continues.
- A fix-it zip is created in `tmp\feedback\pack_fixit_incoming.safe.zip`.

## Notes
- This pack does not change your Local Exec Bridge at 127.0.0.1:8765; the Diagnostics page has a best-effort "Test Local Exec Bridge".
- QR uses an online API if available. For fully-offline QR, drop a local QR JS lib in `web/pwa/` and update `index.html`.
