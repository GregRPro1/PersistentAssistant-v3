param(
  [Parameter(Mandatory=$true)][string]$MasterId
)
$ErrorActionPreference = 'Stop'
$repo = git rev-parse --show-toplevel 2>$null
if (-not $repo) { $repo = "C:\_Repos\PersistentAssistant" }
$repo = [System.IO.Path]::GetFullPath($repo)

$masterDir = Join-Path $repo "_context\$MasterId"
$indexYaml = Join-Path $masterDir "index.yaml"
$activeYaml = Join-Path $repo "_context\active_context.yaml"

if (-not (Test-Path $masterDir)) { New-Item -ItemType Directory -Force -Path $masterDir | Out-Null }

# naive parse of index.yaml for last child line "last_child:"
$lastChild = $null
if (Test-Path $indexYaml) {
  $lines = Get-Content -LiteralPath $indexYaml -Encoding UTF8
  foreach ($l in $lines) {
    if ($l -match '^\s*last_child\s*:\s*(\S+)') { $lastChild = $Matches[1]; break }
  }
}

# Write active context
$now = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
$active = @()
$active += "master_id: $MasterId"
if ($lastChild) { $active += "last_child: $lastChild" }
$active += "loaded_at: $now"
$active | Set-Content -LiteralPath $activeYaml -Encoding UTF8

$env:PAL_MASTER = $MasterId
if ($lastChild) { $env:PAL_CHILD = $lastChild }

Write-Host "Loaded master: $MasterId; last_child: $lastChild"
Write-Host "Active context: $activeYaml"
