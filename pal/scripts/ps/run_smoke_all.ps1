param([switch]$Wait)
$tests = Get-ChildItem .\pal\tests\smoke\ -Filter "PAL-*.ps1" | Sort-Object Name
$jobs = @()
foreach ($t in $tests) {
  $jobs += Start-Job -ScriptBlock { param($p,$n) & pwsh $p -Name $n } -ArgumentList $t.FullName, $t.BaseName
}
Write-Host "Started $($jobs.Count) smoke tests in background."
if ($Wait) {
  Receive-Job -Job $jobs -Wait -AutoRemoveJob | Out-Null
  # after completion, auto-flip statuses
  $python = "$env:VIRTUAL_ENV\Scripts\python.exe"; if (-not (Test-Path $python)) { $python = "python" }
  & $python ".\pal\scripts\py\pal_update_status_from_smoke.py"
  # restart tracker to refresh
  $reqDir = ".\pal\control\requests"; if (-not (Test-Path $reqDir)) { New-Item -ItemType Directory -Force -Path $reqDir | Out-Null }
  $req = Join-Path $reqDir ("{0}.json" -f (Get-Date -Format "yyyyMMdd_HHmmss_fff"))
  '{"command":"restart","target":"tracker","note":"smoke auto-flip after wait"}' | Set-Content $req -Encoding UTF8
} else {
  # non-blocking: recommend running smoke_watch.ps1 in background
  Write-Host "Tip: run pal\\scripts\\ps\\smoke_watch.ps1 for auto-flip while tests finish."
}
