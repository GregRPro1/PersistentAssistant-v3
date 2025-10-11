param([string]$TaskId = "PAL-DEMO")
Set-StrictMode -Version Latest
$ErrorActionPreference = "Continue"

function Get-LanIp {
  try {
    $ip = (Get-NetIPAddress -AddressFamily IPv4 |
      Where-Object {
        $_.IPAddress -notmatch '^169\.' -and $_.IPAddress -notmatch '^127\.' -and
        ($_.IPAddress -match '^(10\.|192\.168\.|172\.(1[6-9]|2[0-9]|3[0-1])\.)')
      } |
      Select-Object -First 1 -ExpandProperty IPAddress)
    return $ip
  } catch { return $null }
}

function Read-Json($p){ try { Get-Content -Raw $p -ErrorAction Stop | ConvertFrom-Json } catch { $null } }

$opsPath = ".\reports\ops\ops_status.json"
$cfgPath = ".\pal\config\pal_watchdog.json"
$smokeDir = ".\reports\smoke"
if (-not (Test-Path $smokeDir)) { New-Item -ItemType Directory -Force -Path $smokeDir | Out-Null }

# Create a PASS smoke artifact
$ts = (Get-Date).ToString("s")
$data = @{ test=$TaskId; ts=$ts; ok=$true; notes="Demo PASS" }
($data | ConvertTo-Json -Depth 4) | Set-Content (Join-Path $smokeDir "$TaskId.json") -Encoding UTF8

# Restart tracker + commit
$reqDir = ".\pal\control\requests"; if (-not (Test-Path $reqDir)) { New-Item -ItemType Directory -Force -Path $reqDir | Out-Null }
('{"command":"restart","target":"tracker"}') | Set-Content (Join-Path $reqDir ("{0}_restart.json" -f (Get-Date -Format "yyyyMMdd_HHmmss"))) -Encoding UTF8
('{"command":"commit_plan","message":"PAL: demo smoke"}') | Set-Content (Join-Path $reqDir ("{0}_commit.json" -f (Get-Date -Format "yyyyMMdd_HHmmss"))) -Encoding UTF8

$ops = Read-Json $opsPath
$phoneUrl = $null
if ($ops -and $ops.phone) {
  $phoneUrl = $ops.phone.url; if (-not $phoneUrl) { $phoneUrl = $ops.phone.lan }
}

if (-not $phoneUrl) {
  # Fallback: compute from config + LAN IP
  $cfg = Read-Json $cfgPath
  $port = 8787
  if ($cfg -and $cfg.web -and $cfg.web.port) { $port = [int]$cfg.web.port }
  $lan = Get-LanIp
  if ($lan) { $phoneUrl = "http://$($lan):$($port)" }
  if (-not $phoneUrl -and $cfg -and $cfg.web -and $cfg.web.host -and $cfg.web.port) {
    $phoneUrl = "http://$($cfg.web.host):$($cfg.web.port)"
  }
}

if ($phoneUrl) { Write-Host "Phone URL: $phoneUrl" -ForegroundColor Green } else { Write-Warning "Phone URL not available yet." }
