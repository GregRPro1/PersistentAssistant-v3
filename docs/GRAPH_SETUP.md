# Microsoft Graph watcher (Personal account)

## Register the app
1. InPrivate window → https://entra.microsoft.com/#view/Microsoft_AAD_RegisteredApps/ApplicationsListBlade
2. Make sure the top-right account is your **Outlook.com** personal account.
3. New registration:
   - Name: `PA Graph Watcher`
   - Supported account types: **Personal Microsoft accounts only**
   - Register.
4. Copy **Application (client) ID**.
5. Authentication → **Allow public client flows** → **Yes** (device code). Save.
6. API permissions → **Microsoft Graph** → Delegated → add **Mail.Read** (and `offline_access` if shown). Save.

## Configure
Edit `config/email_watch_graph.yaml`:
```yaml
enabled: true
client_id: "<YOUR-CLIENT-ID>"
authority: "https://login.microsoftonline.com/consumers"
allow_from:
  - "gprapson@gmail.com"
subject_flag: "[PA:xxxxxx]"   # keep or change; must match your phone mails
save_dir: "_inbox"
processed_dir: "_inbox/processed"
apply_after_download: true
```

## First sign-in
```powershell
pwsh tools\ps1\run_email_watcher_graph.ps1 -DeviceLogin
```
A URL and code will print; open the URL and enter the code, approve as **pa-ops**. A token cache is saved under `.secrets\`.

## Poll and schedule
```powershell
pwsh tools\ps1\one_shot_graph_poll.ps1
pwsh tools\ps1\register_email_watcher_graph.ps1
```
Logs: `reports\ops\email_watch_graph.log`, `email_watch_graph.run.log`.
