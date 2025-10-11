# PAL — Immediate Phone URL Fix Pack

This pack fixes the demo script interpolation error and makes the tracker show the Phone URL immediately, even if the watchdog hasn't populated it yet.

## Apply
cd C:\_Repos\PersistentAssistant
pwsh .\scripts\apply_pack.ps1 -ZipPath "$env:USERPROFILE\Downloads\PAL_PhoneURL_Immediate_Fix_Zip.zip"

## Use
# A) Force ops_status to include phone.* now (optional)
pwsh .\pal\scripts\ps\pal_force_ops_snapshot.ps1

# B) Demo: create a smoke PASS and print the Phone URL (robust)
pwsh .\pal\scripts\ps\pal_demo_verify.ps1 -TaskId PAL-DEMO

# C) Restart tracker via watchdog (if needed)
'{"command":"restart","target":"tracker"}' | Set-Content .\pal\control\requests\restart_tracker.json -Encoding UTF8

Tracker status bar now shows Phone: <url>. The WhatsApp button will use this URL.
