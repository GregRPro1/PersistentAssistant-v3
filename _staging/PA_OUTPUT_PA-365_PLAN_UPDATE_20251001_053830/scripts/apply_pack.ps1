<# 
PA-365 Plan Update — apply
- Appends payload\plan_append.yaml to project\plans\project_plan_v3.yaml
- Creates a timestamped backup if the target exists
#>
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Ensure-Dir([string]$p){ if (-not (Test-Path $p)) { New-Item -ItemType Directory -Force -Path $p | Out-Null } }

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot  = Split-Path -Parent $ScriptDir
Push-Location $RepoRoot
Write-Host "apply_pack: repo root = $RepoRoot"

$payload = Join-Path $ScriptDir '..\payload\plan_append.yaml'
if (-not (Test-Path $payload)) { throw "Missing payload file: $payload" }

$planDir = Join-Path $RepoRoot 'project\plans'
$planFile = Join-Path $planDir 'project_plan_v3.yaml'
Ensure-Dir $planDir

# Backup existing
if (Test-Path $planFile) {
  $ts = Get-Date -Format "yyyyMMdd_HHmmss"
  Copy-Item -Force $planFile "$planFile.bak_$ts"
  Write-Host "[PLAN] Backup: $planFile.bak_$ts"
}

# Append (or create new)
if (Test-Path $planFile) {
  Add-Content -Path $planFile -Value "`r`n`r`n# ---- Plan update appended by pack (PA-365) ----`r`n"
  Get-Content $payload -Raw | Add-Content -Path $planFile
} else {
  Copy-Item -Force $payload $planFile
}

# Commit (no push)
try { git add -A; git commit -m "PA-365: append plan updates (QA gate, CI, named tunnel, release publishing, auth, diagnostics, metrics, startup, secrets, repro)" | Out-Null } catch {}

Write-Host "==== PLAN UPDATE APPLIED ===="
Write-Host "Edited: project\plans\project_plan_v3.yaml"
Write-Host "================================"
