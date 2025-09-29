
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
& python (Join-Path $root 'tools\py\web_mobile_inventory.py') $root
$code=$LASTEXITCODE
if ($code -ne 0) { Write-Error "inventory failed ($code)" }
$md = Join-Path $root 'reports\ops\web_mobile_inventory.md'
if (Test-Path $md) { Get-Content $md -Head 40 }
exit $code
