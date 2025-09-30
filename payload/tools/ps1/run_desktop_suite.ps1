param([int]$Port=8776,[switch]$Email)
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

$root = Find-RepoRoot $PSScriptRoot
Write-Host "Desktop Suite root: $root"

# open firewall
try { & (Join-Path $root 'tools\ps1\open_firewall_port.ps1') -Port $Port -Name "PA Control $Port" } catch {}

# Start LAN server job
$lanJob = Start-Job -Name 'PA-LAN' -ScriptBlock {
  param($root,$Port)
  $env:PA_LAN_HOST='0.0.0.0'; $env:PA_LAN_PORT=$Port
  & python (Join-Path $root 'tools\py\lan_control_server.py')
} -ArgumentList $root,$Port

# Wait for /healthz
$ok = $false
for ($i=0; $i -lt 30; $i++){
  Start-Sleep -Milliseconds 500
  try {
    $r = Invoke-WebRequest ("http://127.0.0.1:{0}/healthz" -f $Port) -UseBasicParsing -TimeoutSec 2
    if ($r.StatusCode -eq 200) { $ok = $true; break }
  } catch {}
}
if (-not $ok) { Write-Warning "LAN server healthz not ready" }

# Start pack fetcher loop job (60s)
$fetchJob = Start-Job -Name 'PA-FETCHER' -ScriptBlock {
  param($root)
  & pwsh (Join-Path $root 'tools\ps1\run_pack_fetcher.ps1') -Loop -IntervalSec 60
} -ArgumentList $root

# Optionally start email watcher loop if enabled or flag set
$emailStarted = $false
try {
  $cfg = Get-Content (Join-Path $root 'config\email_watch.yaml') -Raw
  if ($cfg -match '(?mi)^\s*enabled:\s*true') { $Email = $true }
} catch {}
if ($Email) {
  $emailJob = Start-Job -Name 'PA-EMAIL' -ScriptBlock {
    param($root)
    & pwsh (Join-Path $root 'tools\ps1\run_email_watcher.ps1') -Loop -IntervalSec 60
  } -ArgumentList $root
  $emailStarted = $true
}

# Print endpoints
function Get-PrivateIPv4 {
  $ips = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object {
    $_.IPAddress -match '^\d+\.' -and $_.PrefixOrigin -ne 'WellKnown'
  }).IPAddress
  foreach ($ip in $ips) {
    if ($ip -like '10.*' -or $ip -like '192.168.*') { return $ip }
    $p = $ip.Split('.'); if ($p.Length -eq 4) {
      $a=[int]$p[0]; $b=[int]$p[1]
      if ($a -eq 172 -and $b -ge 16 -and $b -le 31) { return $ip }
    }
  }
  return $null
}

$ip = Get-PrivateIPv4
Write-Host ("Mobile UI: http://127.0.0.1:{0}/app/  (LAN: http://{1}:{0}/app/)" -f $Port, ($ip?$ip:'<no-LAN-IP>'))
Write-Host ("Control:   http://127.0.0.1:{0}/control/" -f $Port)
Write-Host ("Ops:       http://127.0.0.1:{0}/ops/" -f $Port)

# Persist a small status JSON
$status = @{
  time = (Get-Date).ToString('s')
  port = $Port
  jobs = @{
    lan = $lanJob.Id
    fetcher = $fetchJob.Id
    email = if ($emailStarted) { $emailJob.Id } else { $null }
  }
}
$ops = Join-Path $root 'reports\ops'
New-Item -ItemType Directory -Force -Path $ops | Out-Null
$status | ConvertTo-Json -Depth 5 | Set-Content (Join-Path $ops 'desktop_suite_status.json')

Write-Host "Desktop Suite running. Press Ctrl+C in job consoles to stop."
