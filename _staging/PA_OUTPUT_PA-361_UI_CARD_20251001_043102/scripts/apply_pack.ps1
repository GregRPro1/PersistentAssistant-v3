<# 
PA-361 UI Status Card Pack — apply
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

Ensure-Dir "reports\ops"
Ensure-Dir "tmp\logs"

try { git add -A; git commit -m "PA-361: add /api/watchdog and /app/watchdog status card" | Out-Null } catch {}

Write-Host "==== UI STATUS CARD APPLIED ===="
Write-Host "Open:  http://127.0.0.1:8776/app/watchdog"
Write-Host "API :  http://127.0.0.1:8776/api/watchdog"
Write-Host "================================"
