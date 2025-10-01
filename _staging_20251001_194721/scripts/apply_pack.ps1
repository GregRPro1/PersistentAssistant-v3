<# 
PA-370 Watchdog Pack — apply
#>
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Ensure-Dir([string]$p){ if (-not (Test-Path $p)) { New-Item -ItemType Directory -Force -Path $p | Out-Null } }

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot  = Split-Path -Parent $ScriptDir
Push-Location $RepoRoot
Write-Host "apply_pack: repo root = $RepoRoot"

$payload = Join-Path $ScriptDir '..\payload'
if (-not (Test-Path $payload)) { throw "Payload folder not found: $payload" }

$files = Get-ChildItem -Recurse -File $payload
foreach ($f in $files) {
  $rel = $f.FullName.Substring($payload.Length).TrimStart('\','/')
  $dest = Join-Path $RepoRoot $rel
  $destDir = Split-Path $dest -Parent
  Ensure-Dir $destDir
  Copy-Item -Force -Path $f.FullName -Destination $dest
}

Ensure-Dir "tmp\logs"; Ensure-Dir "tmp\pid"; Ensure-Dir "reports\ops"; Ensure-Dir "config"

try { git add -A; git commit -m "PA-370: add watchdog (supervisor + config + run/stop scripts)" | Out-Null } catch {}

Write-Host "==== WATCHDOG PACK APPLIED ===="
Write-Host "Start watchdog (detached):  pwsh tools\ps1\run_watchdog.ps1"
Write-Host "Stop watchdog:              pwsh tools\ps1\stop_watchdog.ps1"
Write-Host "Status JSON:                reports\ops\watchdog_status.json"
Write-Host "==============================="
