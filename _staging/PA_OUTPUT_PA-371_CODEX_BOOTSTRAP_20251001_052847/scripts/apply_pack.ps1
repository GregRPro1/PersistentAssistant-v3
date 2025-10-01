<# 
PA-371 Codex Bootstrap — apply
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

try {
  $homePrompts = Join-Path $env:USERPROFILE ".codex\prompts"
  Ensure-Dir $homePrompts
  Copy-Item -Force -Recurse -Path (Join-Path $RepoRoot "codex\prompts\*") -Destination $homePrompts -ErrorAction SilentlyContinue
  Write-Host "[PACK] Installed prompts to $homePrompts"
} catch {}

Ensure-Dir "tmp\logs"
Ensure-Dir "reports\ops"
Ensure-Dir "tmp\pid"

try { git add -A; git commit -m "PA-371: Codex bootstrap (tasks, prompts, helper scripts)" | Out-Null } catch {}

Write-Host "==== CODEX BOOTSTRAP APPLIED ===="
Write-Host "Install Codex CLI:  npm i -g @openai/codex  (or: winget install OpenAI.CodexCLI)"
Write-Host "Run Codex in this repo:  codex"
Write-Host "Slash prompts: /pa_smoke, /pa_watchdog, /pa_pack_cycle"
