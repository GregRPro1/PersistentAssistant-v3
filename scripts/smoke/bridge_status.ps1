param([string]\ = (git rev-parse --show-toplevel 2>\))
if (-not \) { \ = 'C:\_Repos\PersistentAssistant' }
Write-Host ('Repo: '+\)
\ = Join-Path \ 'reports\ops\ops_status.json'
\  = Join-Path \ 'tmp\bridge_tracker.log'
if (Test-Path \) { Write-Host '[JSON]'; Get-Content -LiteralPath \ -Raw | Write-Host } else { Write-Host '[MISS] ops_status.json' }
if (Test-Path \) { Write-Host '[LOG TAIL]'; Get-Content -LiteralPath \ -Tail 20 | Write-Host } else { Write-Host '[MISS] bridge_tracker.log' }
