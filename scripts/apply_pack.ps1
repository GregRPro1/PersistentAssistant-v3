Param([string]$RepoRoot = "C:\_Repos\PersistentAssistant")
$ErrorActionPreference = "Stop"
Write-Host "=== Applying PAL pack to $RepoRoot ==="
if (-not (Test-Path $RepoRoot)) { throw "Repo root not found: $RepoRoot" }
$git = Get-Command git -ErrorAction SilentlyContinue; if (-not $git) { throw "git not found in PATH" }
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Payload = Join-Path $ScriptDir "..\payload"
Push-Location $RepoRoot
try {
  $branch = "step/PAL20251012A-context-and-cloudflared-smoke"
  git rev-parse --verify $branch 2>$null
  if ($LASTEXITCODE -ne 0) { git checkout -b $branch } else { git checkout $branch }
  $ensure = @("configs","utils","current","scripts\cloudflared","scripts\misc","logs\cloudflared","logs\pal_snapshots")
  foreach ($p in $ensure) { New-Item -ItemType Directory -Path (Join-Path $RepoRoot $p) -Force | Out-Null }
  Copy-Item -Path (Join-Path $Payload "configs\*") -Destination (Join-Path $RepoRoot "configs") -Force
  Copy-Item -Path (Join-Path $Payload "utils\*") -Destination (Join-Path $RepoRoot "utils") -Force
  Copy-Item -Path (Join-Path $Payload "current\*") -Destination (Join-Path $RepoRoot "current") -Force
  Copy-Item -Path (Join-Path $Payload "scripts\cloudflared\*") -Destination (Join-Path $RepoRoot "scripts\cloudflared") -Force
  Copy-Item -Path (Join-Path $Payload "scripts\misc\*") -Destination (Join-Path $RepoRoot "scripts\misc") -Force
  New-Item -ItemType File -Path (Join-Path $RepoRoot "logs\cloudflared\.keep") -Force | Out-Null
  git add configs utils current scripts logs
  git commit -m "PAL20251012A-fix2: robust server_wrapper, improved smoke test, PAL process snapshot" | Out-Null
  Write-Host "=== PACK/STATUS: Applied and committed on $branch ==="
} finally { Pop-Location }
