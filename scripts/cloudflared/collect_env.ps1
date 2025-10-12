Param([string]$OutDir = "C:\_Repos\PersistentAssistant\logs\cloudflared")
$ErrorActionPreference = "Stop"
New-Item -ItemType Directory -Path $OutDir -Force | Out-Null
$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$log = Join-Path $OutDir "env_$stamp.txt"
"=== ENV DIAGNOSTICS $stamp ===" | Tee-Object -FilePath $log
"`n# PowerShell" | Tee-Object -FilePath $log -Append; $PSVersionTable | Out-String | Tee-Object -FilePath $log -Append
"`n# Network config" | Tee-Object -FilePath $log -Append; ipconfig /all 2>&1 | Tee-Object -FilePath $log -Append
"`n# Routes" | Tee-Object -FilePath $log -Append; route print 2>&1 | Tee-Object -FilePath $log -Append
"`n# Firewall state" | Tee-Object -FilePath $log -Append; netsh advfirewall show allprofiles 2>&1 | Tee-Object -FilePath $log -Append
"`n# Listeners" | Tee-Object -FilePath $log -Append; netstat -ano | Select-String -Pattern "LISTENING" | Tee-Object -FilePath $log -Append
"`n# DNS test" | Tee-Object -FilePath $log -Append; nslookup www.cloudflare.com 2>&1 | Tee-Object -FilePath $log -Append
"`n# curl 127.0.0.1:8787" | Tee-Object -FilePath $log -Append; try { curl.exe -s -I http://127.0.0.1:8787 | Tee-Object -FilePath $log -Append } catch { $_ | Out-String | Tee-Object -FilePath $log -Append }
"`n# Processes" | Tee-Object -FilePath $log -Append; Get-Process | Where-Object { $_.Name -match "cloudflared|python|server" } | Format-Table -AutoSize | Out-String | Tee-Object -FilePath $log -Append
"`n# cloudflared version" | Tee-Object -FilePath $log -Append; ($c=Get-Command cloudflared -ErrorAction SilentlyContinue) ? (cloudflared --version 2>&1 | Tee-Object -FilePath $log -Append) : ("cloudflared not found" | Tee-Object -FilePath $log -Append)
"`nDone -> $log" | Tee-Object -FilePath $log -Append; Write-Host "Wrote $log"
