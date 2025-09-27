param([string]$RepoRoot="")
$ErrorActionPreference='Stop'
function Find-RepoRoot([string]$start){
  try { $p = (Resolve-Path $start).Path } catch { $p = $start }
  while($p -and -not (Test-Path (Join-Path $p '.git'))){
    $parent = Split-Path -Parent $p
    if ($parent -eq $p -or [string]::IsNullOrEmpty($parent)) { break }
    $p = $parent
  }
  if (Test-Path (Join-Path $p '.git')) { return $p } else { return $null }
}
try { & python -V | Out-Null; $py='python' } catch { try { & py -3 -V | Out-Null; $py='py -3' } catch { $py=$null } }
if (-not $py) { Write-Error 'Python 3 not found on PATH'; exit 1 }
$script = Join-Path $PSScriptRoot 'apply_pack.py'
if (-not $RepoRoot -or -not (Test-Path (Join-Path $RepoRoot '.git'))) {
  $RepoRoot = Find-RepoRoot $PSScriptRoot
}
if (-not $RepoRoot) { $RepoRoot = 'C:\_Repos\PersistentAssistant' }
$argsList = @('--repo-root', $RepoRoot)
& $py $script @argsList
exit $LASTEXITCODE
