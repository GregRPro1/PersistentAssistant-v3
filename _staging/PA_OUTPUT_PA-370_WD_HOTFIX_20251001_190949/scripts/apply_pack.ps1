<# 
PA-370 Watchdog Hotfix — apply
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

try { git add -A; git commit -m "PA-370: watchdog hotfix (run by path; add __init__)" | Out-Null } catch {}

Write-Host "==== WATCHDOG HOTFIX APPLIED ===="
Write-Host "Start watchdog: pwsh tools\ps1\run_watchdog.ps1"
