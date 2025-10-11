# Force-write ops_status.json with phone.lan/url computed from LAN + config, preserving existing fields if present
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

$opsPath = ".\reports\ops\ops_status.json"
$cfgPath = ".\pal\config\pal_watchdog.json"
$ops = Read-Json $opsPath; if (-not $ops) { $ops = [ordered]@{} }
$cfg = Read-Json $cfgPath
$port = 8787
if ($cfg -and $cfg.web -and $cfg.web.port) { $port = [int]$cfg.web.port }
$lan = Get-LanIp
$lanUrl = if ($lan) { "http://$($lan):$($port)" } else { "" }

$tunnelUrl = ""
if ($ops -and $ops.tunnel -and $ops.tunnel.url) { $tunnelUrl = [string]$ops.tunnel.url }

# Build phone hashtable without inline 'if' expressions
$phone = [ordered]@{}
$phone.lan = $lanUrl
if ($tunnelUrl) { $phone.url = $tunnelUrl } else { $phone.url = $lanUrl }

$ops.phone = $phone
$ops.ts = (Get-Date).ToString("s")
$ops | ConvertTo-Json -Depth 6 | Set-Content $opsPath -Encoding UTF8
Write-Host "ops_status.json updated. phone.url=$($ops.phone.url)"
