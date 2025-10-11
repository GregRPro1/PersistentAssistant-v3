# Print Phone URL (with fallback computation if missing)
Set-StrictMode -Version Latest
$ErrorActionPreference = "Continue"

function Read-Json($p){ try { Get-Content -Raw $p -ErrorAction Stop | ConvertFrom-Json } catch { $null } }
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
$ops = Read-Json ".\reports\ops\ops_status.json"
$cfg = Read-Json ".\pal\config\pal_watchdog.json"

$port = 8787
if ($cfg -and $cfg.web -and $cfg.web.port) { $port = [int]$cfg.web.port }

$url = $null
if ($ops -and $ops.phone) { $url = $ops.phone.url; if (-not $url) { $url = $ops.phone.lan } }
if (-not $url) {
  $lan = Get-LanIp
  if ($lan) { $url = "http://$($lan):$($port)" }
  elseif ($cfg -and $cfg.web -and $cfg.web.host) { $url = "http://$($cfg.web.host):$($port)" }
}

if ($url) { Write-Host "Phone URL: $url" -ForegroundColor Green } else { Write-Warning "No Phone URL computed." }
