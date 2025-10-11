param([Parameter(Mandatory=$true)][string]$Phase, [switch]$Wait)
# Ensure stubs exist for each task in phase
pwsh .\pal\scripts\ps\gen_smoke_for_phase.ps1 -Phase $Phase | Out-Null
# Run them all
$tests = Get-ChildItem ".\pal\tests\smoke" -Filter "$Phase-*.ps1" -File
if (-not $tests) {
  # fallback: run all PAL-*.ps1 and let watcher auto-flip
  $tests = Get-ChildItem ".\pal\tests\smoke" -Filter "PAL-*.ps1" -File
}
$jobs = @()
foreach ($t in $tests) {
  $jobs += Start-Job -ScriptBlock { param($p,$n) & pwsh $p -Name $n } -ArgumentList $t.FullName, $t.BaseName
}
Write-Host "Started $($jobs.Count) smoke tests for phase $Phase."
if ($Wait) {
  Receive-Job -Job $jobs -Wait -AutoRemoveJob | Out-Null
  # auto-flip & refresh
  $python = "$env:VIRTUAL_ENV\Scripts\python.exe"; if (-not (Test-Path $python)) { $python = "python" }
  & $python ".\pal\scripts\py\pal_update_status_from_smoke.py"
  $reqDir = ".\pal\control\requests"; if (-not (Test-Path $reqDir)) { New-Item -ItemType Directory -Force -Path $reqDir | Out-Null }
  $req = Join-Path $reqDir ("{0}.json" -f (Get-Date -Format "yyyyMMdd_HHmmss_fff"))
  '{"command":"restart","target":"tracker","note":"phase smoke finished"}' | Set-Content $req -Encoding UTF8
} else {
  Write-Host "Non-blocking: start watcher with 'Start-Job -ScriptBlock {{ pwsh .\pal\scripts\ps\smoke_watch.ps1 }}'"
}
