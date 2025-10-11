# PAL — Watchdog Fix + WhatsApp Share + Settings

This pack:
- Fixes the watchdog PowerShell parse error (string interpolation) and publishes both **LAN** and unified **Phone URL**.
- Adds a **WhatsApp** button in the tracker status bar:
  - **wa_me** mode: opens a WhatsApp compose URL in your browser (no credentials required).
  - **cloud_api** mode: sends via **Meta WhatsApp Cloud API** (needs token + phone_number_id + to_number).
- Adds a **Settings** dialog in the tracker to configure WhatsApp parameters; config stored at `pal/config/pal_ui.json`.

## Apply
```powershell
cd C:\_Repos\PersistentAssistant
pwsh .\scripts\apply_pack.ps1 -ZipPath "$env:USERPROFILE\Downloads\PAL_Watchdog_Fix_WhatsApp_Button_Settings.zip"
```

## Run
```powershell
pwsh .\pal\core\health\watchdog.ps1
# Then (or already running) start/update the tracker
# The tracker reads ops_status.json emitted by the watchdog for the Phone URL.
```

## Configure WhatsApp
In the tracker, click **⚙ Settings** (top-right next to actions), then:
- **Method**: choose **wa_me** (simple) or **cloud_api**.
- For **wa_me**, optionally add a **to_number** (E.164). If omitted, WhatsApp will open a contact picker.
- For **cloud_api**, fill **phone_number_id**, **access_token**, **to_number**.

Then press **Send to WhatsApp** on the status bar; it shares the current **Phone URL** (tunnel preferred, otherwise LAN).

Generated: 2025-10-11
