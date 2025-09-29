param([switch]$Once, [int]$IntervalSeconds = 60, [int]$Tail = 80)
$ErrorActionPreference='Stop'

function Find-RepoRoot([string]$start) {
  if (-not $start) { $start = $PSScriptRoot }
  $cur = Resolve-Path -LiteralPath $start
  for ($i=0; $i -lt 10; $i++) {
    if (Test-Path (Join-Path $cur '.git')) { return $cur }
    $parent = Split-Path -Parent $cur
    if ($parent -eq $cur) { break }
    $cur = $parent
  }
  return (Get-Location).Path
}

$root = Find-RepoRoot $null
$py = Join-Path $root 'tools\py\pack_fetcher.py'
if (-not (Test-Path $py)) { Write-Error "pack_fetcher.py not found at $py"; exit 2 }

Write-Host "run_pack_fetcher: root=$root"
if ($Once) {
  & python $py --once
} else {
  & python $py --interval $IntervalSeconds
}
$code = $LASTEXITCODE
Write-Host "run_pack_fetcher: exit $code"

$log = Join-Path $root 'reports\ops\pack_fetcher.log'
if (Test-Path $log) {
  Write-Host "---- tail pack_fetcher.log (last $Tail lines) ----"
  Get-Content $log -Tail $Tail
} else {
  Write-Host "pack_fetcher.log not found yet."
}
exit $code