param([Parameter(Mandatory = $true)][string]$ZipPath)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Ensure-Dir([string]$p) { if (-not (Test-Path $p)) { New-Item -ItemType Directory -Force -Path $p | Out-Null } }

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $ScriptDir
Push-Location $RepoRoot
Write-Host "apply_pack: repo root = $RepoRoot"

# 1) Expand ZIP to temp
$TempDir = Join-Path $RepoRoot "_tmp_pack_$(Get-Date -Format yyyyMMdd_HHmmss_fff)"
Ensure-Dir $TempDir
Expand-Archive -Path $ZipPath -DestinationPath $TempDir -Force

# 2) If plan append exists, append to legacy plan
$planAppend = Join-Path $TempDir 'payload\plan_append.yaml'
$planDir = Join-Path $RepoRoot 'project\plans'
$planFile = Join-Path $planDir 'project_plan_v3.yaml'
Ensure-Dir $planDir

if (Test-Path $planAppend) {
  if (Test-Path $planFile) {
    $ts = Get-Date -Format "yyyyMMdd_HHmmss"
    Copy-Item -Force $planFile "$planFile.bak_$ts"
    Write-Host "[PLAN] Backup: $planFile.bak_$ts"
    Add-Content -Path $planFile -Value "`r`n`r`n# ---- Plan update appended by pack ----`r`n"
    Get-Content $planAppend -Raw | Add-Content -Path $planFile
  }
  else {
    Copy-Item -Force $planAppend $planFile
  }
}

# 3) Copy payload/* into repo
$payloadRoot = Join-Path $TempDir "payload"
if (Test-Path $payloadRoot) {
  Copy-Item "$payloadRoot\*" -Destination $RepoRoot -Recurse -Force
  Write-Host "Applied payload/ to $RepoRoot"
}

# 4) Cleanup temp
Remove-Item $TempDir -Recurse -Force

# 5) Commit
try { git add -A; git commit -m "apply_pack: apply payload and optional plan append from $([IO.Path]::GetFileName($ZipPath))" | Out-Null } catch {}

Write-Host "==== PACK APPLIED ===="
Pop-Location
