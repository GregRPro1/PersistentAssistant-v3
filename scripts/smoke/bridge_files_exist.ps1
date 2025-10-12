# bridge_files_exist.ps1 — simple pass/fail
\ = git rev-parse --show-toplevel 2>$null
if (-not \) { \ = 'C:\_Repos\PersistentAssistant' }
\ = True
foreach (\ in @('reports\ops\ops_status.json','tmp\bridge_tracker.log')) {
  \ = Join-Path \ \
  if (-not (Test-Path \)) { Write-Host ('[MISS] '+\); \ = False } else { Write-Host ('[OK] '+\) }
}
if (-not \) { exit 1 }
