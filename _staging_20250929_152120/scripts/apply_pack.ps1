param([string]$RepoRoot='')
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
$root = if ($RepoRoot) { Resolve-Path -LiteralPath $RepoRoot } else { Find-RepoRoot $PSScriptRoot }
$ops = Join-Path $root 'reports\ops'
New-Item -ItemType Directory -Force -Path $ops | Out-Null
$marker = Join-Path $ops 'hello_pack_applied.txt'
$stamp = Get-Date -AsUTC -Format 'yyyyMMdd_HHmmssZ'
"HELLO PACK APPLIED $stamp" | Out-File -Encoding utf8 -FilePath $marker -Append
Write-Host "HELLO PACK: marker written to $marker"
exit 0