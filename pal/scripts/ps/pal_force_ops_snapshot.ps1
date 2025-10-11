# Force-write ops_status.json with phone.lan/url computed from LAN + config.
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Read-Json($p){ try { Get-Content -Raw $p -ErrorAction Stop | ConvertFrom-Json } catch { $null } }

function PSCustomObject-ToHashtable([object]$obj){
  if ($null -eq $obj) { return @{} }
  if ($obj -is [hashtable]) { return $obj }
  $ht = @{}; foreach ($p in $obj.PSObject.Properties){
    $val = $p.Value
    if ($val -is [System.Management.Automation.PSCustomObject]) { $val = PSCustomObject-ToHashtable $val }
    $ht[$p.Name] = $val
  }
  return $ht
}

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

$opsObj = Read-Json $opsPath
$ops = PSCustomObject-ToHashtable $opsObj  # <- use hashtable so we can set new keys

# pull config/port
$cfg = Read-Json $cfgPath
$port = 8787
if ($cfg -and $cfg.web -and $cfg.web.port) { $port = [int]$cfg.web.port }

# compute urls
$lan = Get-LanIp
$lanUrl = if ($lan) { "http://$($lan):$($port)" } else { "" }
$tunnelUrl = ""
if ($ops.ContainsKey("tunnel") -and $ops.tunnel -and $ops.tunnel.url) { $tunnelUrl = [string]$ops.tunnel.url }

# assign phone
$phone = @{}
$phone.lan = $lanUrl
$phone.url = if ($tunnelUrl) { $tunnelUrl } else { $lanUrl }
$ops["phone"] = $phone
$ops["ts"] = (Get-Date).ToString("s")

# write
$ops | ConvertTo-Json -Depth 8 | Set-Content $opsPath -Encoding UTF8

Write-Host ("ops_status.json updated. phone.lan={0} phone.url={1}" -f $phone.lan, $phone.url)
