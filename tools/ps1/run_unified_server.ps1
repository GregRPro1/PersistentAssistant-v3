param()
$ErrorActionPreference = 'Stop'

function Find-RepoRoot([string]$start) {
  if ([string]::IsNullOrWhiteSpace($start)) {
    if ($PSScriptRoot -and $PSScriptRoot.Trim()) { $start = $PSScriptRoot }
    elseif ($MyInvocation.MyCommand.Path) { $start = Split-Path -Parent $MyInvocation.MyCommand.Path }
    else { $start = (Get-Location).Path }
  }
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
Write-Host "Unified server root: $root"
& python (Join-Path $root 'tools\py\unified_server.py')
exit $LASTEXITCODE
