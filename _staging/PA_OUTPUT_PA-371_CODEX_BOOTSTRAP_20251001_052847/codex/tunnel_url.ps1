Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$report = "reports\ops\tunnel_url.txt"
if (Test-Path $report) { (Get-Content $report -TotalCount 1); exit 0 }
$log = Get-ChildItem tmp\logs\cloudflared*.log -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if ($null -eq $log) { Write-Host "(no tunnel_url.txt and no cloudflared log)"; exit 1 }
$match = Select-String -Path $log.FullName -Pattern 'https?://\S*trycloudflare\.com' -AllMatches -ErrorAction SilentlyContinue
if ($match -and $match.Matches.Count -gt 0) { $match.Matches[0].Value; exit 0 }
Write-Host "(no URL found yet)"; exit 2
