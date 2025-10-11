param([switch]$Wait)
$tests = @('PAL-101','PAL-102','PAL-103','PAL-104','PAL-105','PAL-106')
$jobs = @()
foreach ($t in $tests) {
  $path = ".\pal\tests\smoke\$t.ps1"
  if (Test-Path $path) {
    $jobs += Start-Job -ScriptBlock { param($p,$n) & pwsh $p -Name $n } -ArgumentList $path, $t
  } else {
    Write-Warning "Missing test: $path"
  }
}
Write-Host "Started $($jobs.Count) smoke tests in background."
if ($Wait) {
  Receive-Job -Job $jobs -Wait -AutoRemoveJob
} else {
  # non-blocking; leave jobs running
  $jobs | ForEach-Object { Write-Host ("Job {0} -> {1}" -f $_.Id, $_.Name) }
}
