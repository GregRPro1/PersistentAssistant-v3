param([int]$Port = 8770)
$ErrorActionPreference = "Stop"

function Get-PrimaryIPv4 {
  $cand = Get-NetIPAddress -AddressFamily IPv4 -PrefixOrigin Dhcp -ErrorAction SilentlyContinue |
          Where-Object { $_.IPAddress -ne "127.0.0.1" -and $_.ValidLifetime -gt 0 } |
          Sort-Object -Property SkipAsSource, InterfaceMetric, PrefixLength
  if (!$cand) {
    $cand = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
            Where-Object { $_.IPAddress -ne "127.0.0.1" }
  }
  return ($cand | Select-Object -First 1).IPAddress
}

function Ensure-FirewallRule { param([int]$Port,[string]$Name="PA Phone Preview")
  $exist = Get-NetFirewallRule -DisplayName $Name -ErrorAction SilentlyContinue
  if (!$exist) {
    New-NetFirewallRule -DisplayName $Name -Direction Inbound -Action Allow -Protocol TCP -LocalPort $Port | Out-Null
  }
}

$ip = Get-PrimaryIPv4
$listen = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue

$result = [ordered]@{
  time = (Get-Date).ToString("s")
  ip = $ip
  port = $Port
  listening = [bool]$listen
  firewall_rule = "checked/ensured"
  localhost_ping = $false
  lan_ping = $false
  notes = @()
}

Ensure-FirewallRule -Port $Port

try {
  $u = ("http://{0}:{1}/ping" -f "127.0.0.1", $Port)
  Invoke-WebRequest -UseBasicParsing -Uri $u -TimeoutSec 2 | Out-Null
  $result.localhost_ping = $true
} catch {
  $result.notes += "Localhost /ping failed: $($_.Exception.Message)"
}

if ($ip) {
  try {
    $u2 = ("http://{0}:{1}/ping" -f $ip, $Port)
    Invoke-WebRequest -UseBasicParsing -Uri $u2 -TimeoutSec 2 | Out-Null
    $result.lan_ping = $true
  } catch {
    $result.notes += "LAN /ping failed: $($_.Exception.Message)"
  }
} else {
  $result.notes += "No primary IPv4 detected."
}

$resultPath = "tmp\logs\lan_diag.json"
$result | ConvertTo-Json -Depth 5 | Set-Content -Path $resultPath -Encoding UTF8
Write-Host "[LAN DIAG]" (Get-Content $resultPath -Raw)
