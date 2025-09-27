$ErrorActionPreference='Stop'
$inbox = Join-Path $PSScriptRoot '..\_inbox' | Resolve-Path -ErrorAction SilentlyContinue
if (-not $inbox) { $inbox = '_inbox' }
$inbox = [string]$inbox
if (-not (Test-Path $inbox)) { New-Item -ItemType Directory -Force -Path $inbox | Out-Null }
$packs = Get-ChildItem -Path $inbox -Filter '*.zip' -File -ErrorAction SilentlyContinue
foreach($p in $packs){
  Write-Host "Applying pack: $($p.FullName)"
  pwsh (Join-Path $PSScriptRoot '..\apply_packs_only.ps1') -ZipPath $p.FullName
  if ($LASTEXITCODE -eq 0){
    $dest = Join-Path $inbox ('processed_' + (Get-Date -Format 'yyyyMMdd_HHmm'))
    New-Item -ItemType Directory -Force -Path $dest | Out-Null
    Move-Item $p.FullName $dest -Force
  } else {
    Write-Host "Pack failed: $($p.FullName)"
  }
}
