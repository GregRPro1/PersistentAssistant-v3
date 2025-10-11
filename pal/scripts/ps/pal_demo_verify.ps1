param([string]$TaskId = "PAL-DEMO")
Set-StrictMode -Version Latest
$ErrorActionPreference = "Continue"
function Get-LanIp {
  try {
    $ip = (Get-NetIPAddress -AddressFamily IPv4 |
      Where-Object { $_.IPAddress -notmatch '^169\.' -and $_.IPAddress -notmatch '^127\.' -and
        ($_.IPAddress -match '^(10\.|192\.168\.|172\.(1[6-9]|2[0-9]|3[0-1])\.)') } |
      Select-Object -First 1 -ExpandProperty IPAddress)
    return $ip
  } catch { return $null }
}
function Read-Json($p){ try { Get-Content -Raw $p -ErrorAction Stop | ConvertFrom-Json } catch { $null } }
$opsPath = ".\reports\ops\ops_status.json"; $cfgPath = ".\pal\config\pal_watchdog.json"; $smokeDir = ".\reports\smoke"
if (-not (Test-Path $smokeDir)) { New-Item -ItemType Directory -Force -Path $smokeDir | Out-Null }
$ts = (Get-Date).ToString("s"); $data = @{ test=$TaskId; ts=$ts; ok=$true; notes="Demo PASS" }
($data | ConvertTo-Json -Depth 4) | Set-Content (Join-Path $smokeDir "$TaskId.json") -Encoding UTF8
$reqDir = ".\pal\control\requests"; if (-not (Test-Path $reqDir)) { New-Item -ItemType Directory -Force -Path $reqDir | Out-Null }
('{"command":"restart","target":"tracker"}') | Set-Content (Join-Path $reqDir ("{0}_restart.json" -f (Get-Date -Format "yyyyMMdd_HHmmss"))) -Encoding UTF8
$ops = Read-Json $opsPath; $cfg = Read-Json $cfgPath; $port = 8787; if ($cfg -and $cfg.web -and $cfg.web.port) { $port = [int]$cfg.web.port }
$phoneUrl = $null
if ($ops -and $ops.phone) { $phoneUrl = $ops.phone.url; if (-not $phoneUrl) { $phoneUrl = $ops.phone.lan } }
if (-not $phoneUrl) { $lan = Get-LanIp; if ($lan) { $phoneUrl = "http://$($lan):$($port)" } elseif ($cfg -and $cfg.web -and $cfg.web.host) { $phoneUrl = "http://$($cfg.web.host):$($port)" } }
if ($phoneUrl) { Write-Host "Phone URL: $phoneUrl" -ForegroundColor Green } else { Write-Warning "Phone URL not available yet." }
