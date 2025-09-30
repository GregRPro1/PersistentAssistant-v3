param(
  [string]$Listen='0.0.0.0',
  [int]$Port=8776
)
$ErrorActionPreference='Stop'

function Find-RepoRoot([string]$start) {
  if (-not $start) { $start = $PSScriptRoot }
  $cur = Resolve-Path -LiteralPath $start
  for ($i=0; $i -lt 12; $i++) {
    if (Test-Path (Join-Path $cur '.git')) { return $cur }
    $parent = Split-Path -Parent $cur
    if ($parent -eq $cur) { break }
    $cur = $parent
  }
  return (Get-Location).Path
}

function Get-PrivateIPv4() {
  $ips = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object {
    $_.IPAddress -match '^\d+\.' -and $_.PrefixOrigin -ne 'WellKnown'
  }).IPAddress
  foreach ($ip in $ips) {
    if ($ip -like '10.*' -or $ip -like '192.168.*') { return $ip }
    # 172.16.0.0 - 172.31.255.255
    $p = $ip.Split('.'); if ($p.Length -eq 4) {
      $a=[int]$p[0]; $b=[int]$p[1]
      if ($a -eq 172 -and $b -ge 16 -and $b -le 31) { return $ip }
    }
  }
  return $null
}

$root = Find-RepoRoot $PSScriptRoot
$env:PA_LAN_HOST = $Listen
$env:PA_LAN_PORT = $Port

# best-effort firewall open
try { & (Join-Path $root 'tools\ps1\open_firewall_port.ps1') -Port $Port -Name "PA Control $Port" } catch { }

$lan = Join-Path $root 'tools\py\lan_control_server.py'
$ip = Get-PrivateIPv4
if ($ip) { Write-Host ("Browse (LAN): http://{0}:{1}/app/" -f $ip,$Port) }
Write-Host ("Browse (Local): http://127.0.0.1:{0}/app/" -f $Port)

# Run server
& python $lan
exit $LASTEXITCODE
