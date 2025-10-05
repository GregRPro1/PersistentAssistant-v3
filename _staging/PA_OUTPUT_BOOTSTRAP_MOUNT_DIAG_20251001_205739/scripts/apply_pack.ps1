<# 
PA Bootstrap Mount Diagnostics (non-blocking)
- Copies payload/*
- Ensures processes.json server runner set to server.bootstrap_mounts (idempotent)
- Restarts watchdog
- No blocking prompts; writes mount logs to tmp\logs\bootstrap_mounts.log
#>
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Ensure-Dir([string]$p){ if (-not (Test-Path $p)) { New-Item -ItemType Directory -Force -Path $p | Out-Null } }

$RepoRoot = Get-Location
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Payload  = Join-Path $ScriptDir '..\payload'

Write-Host "apply_pack: repo root = $RepoRoot"
if (-not (Test-Path $Payload)) { throw "Payload folder not found: $Payload" }

# 1) Copy payload files
$files = Get-ChildItem -Recurse -File $Payload
foreach ($f in $files) {
  $rel = $f.FullName.Substring($Payload.Length).TrimStart('\','/')
  $dest = Join-Path $RepoRoot $rel
  $destDir = Split-Path $dest -Parent
  Ensure-Dir $destDir
  Copy-Item -Force -Path $f.FullName -Destination $dest
}

# 2) Ensure server uses bootstrap runner (idempotent)
$cfgPath = Join-Path $RepoRoot 'config\processes.json'
$cfg = $null
if (Test-Path $cfgPath) {
  try { $cfg = ConvertFrom-Json -AsHashtable -InputObject (Get-Content $cfgPath -Raw) } catch { $cfg = @{} }
} else { $cfg = @{} }
if (-not $cfg.ContainsKey('processes') -or ($cfg.processes -isnot [hashtable])) { $cfg['processes'] = @{} }

$venvPy = Join-Path $RepoRoot '.venv\Scripts\python.exe'
$pyExe  = (Test-Path $venvPy) ? $venvPy : 'python'

$cfg['processes']['server'] = @{
  name = 'server'
  cmd  = @($pyExe,'-u','-m','server.bootstrap_mounts')
}

Ensure-Dir (Split-Path $cfgPath -Parent)
($cfg | ConvertTo-Json -Depth 12) | Set-Content -Encoding UTF8 $cfgPath

# 3) Restart watchdog
try { pwsh -NoProfile -ExecutionPolicy Bypass -File (Join-Path $RepoRoot 'tools\ps1\stop_watchdog.ps1') | Out-Null } catch {}
pwsh -NoProfile -ExecutionPolicy Bypass -File (Join-Path $RepoRoot 'tools\ps1\run_watchdog.ps1') | Out-Null
Start-Sleep 3

Write-Host "==== MOUNT DIAG PACK APPLIED ===="
Write-Host "Mount log: tmp\logs\bootstrap_mounts.log"
