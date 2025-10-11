# Emits a demo smoke result and prints the Phone URL from ops status
param([string]$TaskId = "PAL-DEMO")
Set-StrictMode -Version Latest
$ErrorActionPreference = "Continue"

$ops = ".\reports\ops\ops_status.json"
$smokeDir = ".\reports\smoke"
if (-not (Test-Path $smokeDir)) { New-Item -ItemType Directory -Force -Path $smokeDir | Out-Null }

# Create a PASS smoke artifact
$ts = (Get-Date).ToString("s")
$data = @{ test=$TaskId; ts=$ts; ok=$true; notes="Demo PASS" }
($data | ConvertTo-Json -Depth 4) | Set-Content (Join-Path $smokeDir "$TaskId.json") -Encoding UTF8

# Nudge tracker + commit
$reqDir = ".\pal\control\requests"; if (-not (Test-Path $reqDir)) { New-Item -ItemType Directory -Force -Path $reqDir | Out-Null }
('{"command":"restart","target":"tracker"}') | Set-Content (Join-Path $reqDir ("{0}_restart.json" -f (Get-Date -Format "yyyyMMdd_HHmmss"))) -Encoding UTF8
('{"command":"commit_plan","message":"PAL: demo smoke"}') | Set-Content (Join-Path $reqDir ("{0}_commit.json" -f (Get-Date -Format "yyyyMMdd_HHmmss"))) -Encoding UTF8

# Print the Phone URL if present
if (Test-Path $ops) {
  $o = Get-Content -Raw $ops | ConvertFrom-Json
  $url = $o.phone.url
  if (-not $url) { $url = $o.phone.lan }
  if ($url) { Write-Host "Phone URL: $url" -ForegroundColor Green } else { Write-Warning "Phone URL not available yet." }
} else {
  Write-Warning "ops_status.json not found. Start the watchdog first."
}
