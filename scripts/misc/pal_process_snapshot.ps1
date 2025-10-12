Param(
  [string]$RepoRoot = "C:\_Repos\PersistentAssistant",
  [string]$Tag = "snapshot"
)
$ErrorActionPreference = "Stop"
$OutDir = Join-Path $RepoRoot "logs\pal_snapshots"
New-Item -ItemType Directory -Path $OutDir -Force | Out-Null
$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$log = Join-Path $OutDir "pal_process_$($Tag)_$stamp.txt"

"=== PAL PROCESS SNAPSHOT $stamp ($Tag) ===" | Tee-Object -FilePath $log
"`n# PSVersion" | Tee-Object -FilePath $log -Append; $PSVersionTable | Out-String | Tee-Object -FilePath $log -Append
"`n# Processes (python, cloudflared, node, nginx, gunicorn, uvicorn)" | Tee-Object -FilePath $log -Append
Get-Process | Where-Object { $_.Name -match "python|cloudflared|node|nginx|gunicorn|uvicorn" } | Format-Table -AutoSize | Out-String | Tee-Object -FilePath $log -Append
"`n# Listeners (common dev ports)" | Tee-Object -FilePath $log -Append
netstat -ano | Select-String -Pattern "LISTENING" | Tee-Object -FilePath $log -Append
"`n# cloudflared tunnels" | Tee-Object -FilePath $log -Append
try { cloudflared tunnel list --output json 2>&1 | Tee-Object -FilePath $log -Append } catch { $_ | Out-String | Tee-Object -FilePath $log -Append }
"`nDone -> $log" | Tee-Object -FilePath $log -Append

# Commit snapshot so remote assistant can inspect
Push-Location $RepoRoot
try {
  git add "logs\pal_snapshots\*.txt"
  git commit -m "PAL snapshot: $Tag at $stamp" | Out-Null
} catch {
  Write-Warning "Git commit failed (maybe no changes)."
} finally {
  Pop-Location
}
Write-Host "=== PACK/STATUS: Snapshot written and (attempted) commit ==="
