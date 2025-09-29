param([switch]$Once, [int]$IntervalSeconds = 60)
$ErrorActionPreference='Stop'

function Find-RepoRoot([string]$start) {
  $cur = Resolve-Path -LiteralPath $start
  for ($i=0; $i -lt 10; $i++) {
    if (Test-Path (Join-Path $cur '.git')) { return $cur }
    $parent = Split-Path -Parent $cur
    if ($parent -eq $cur) { break }
    $cur = $parent
  }
  return (Get-Location).Path
}

$root = Find-RepoRoot $PSScriptRoot
$py = Join-Path $root 'tools\py\pack_fetcher.py'

if ($Once) {
  & python $py --once
} else {
  & python $py --interval $IntervalSeconds
}
exit $LASTEXITCODE