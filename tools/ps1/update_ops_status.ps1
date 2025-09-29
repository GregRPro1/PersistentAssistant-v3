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
& python (Join-Path $root 'tools\py\ops_status_html.py')
$code=$LASTEXITCODE
if ($code -ne 0) { Write-Error "status update failed ($code)" }
$ix = Join-Path $root 'docs\ops\index.html'
if (Test-Path $ix) { Write-Host "Status HTML: $ix" }
exit $code
