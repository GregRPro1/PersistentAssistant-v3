
param(
  [string]$RepoRoot
)

$ErrorActionPreference = 'Stop'

function Get-RepoRoot {
  param([string]$Hint)
  if ($Hint -and (Test-Path $Hint)) { return (Resolve-Path $Hint).Path }
  $cwd = (Get-Location).Path
  if (Test-Path (Join-Path $cwd 'tools\ps1')) { return $cwd }
  $parent = Split-Path -Parent $PSScriptRoot
  $parent2 = Split-Path -Parent $parent
  if (Test-Path (Join-Path $parent2 'tools\ps1')) { return $parent2 }
  return $cwd
}

$repo = Get-RepoRoot -Hint $RepoRoot
$packRoot = Split-Path -Parent $PSScriptRoot
$payload = Join-Path $packRoot 'payload'

Write-Host "Repo root: $repo"
Write-Host "Payload : $payload"

$items = Get-ChildItem -Path $payload -Recurse -File
foreach($it in $items){
  $rel = $it.FullName.Substring($payload.Length).TrimStart('\','/')
  $dest = Join-Path $repo $rel
  New-Item -ItemType Directory -Force (Split-Path -Parent $dest) | Out-Null
  Copy-Item -LiteralPath $it.FullName -Destination $dest -Force
  Write-Host ("Updated {0}" -f $dest)
}

Write-Host "==== Admin Toolset applied ===="
Write-Host "Status (watch-only):  pwsh tools\ps1\pa_status.ps1 -Watch"
Write-Host "Auto-recover once:   pwsh tools\ps1\pa_status.ps1 -AutoRecover"
Write-Host "Deep smoke tests:    pwsh tools\ps1\deep_smoke.ps1 -Restart"
