
param(
  [switch]$Watch,
  [int]$IntervalSeconds = 8,
  [switch]$AutoRecover,
  [int]$TimeoutSec = 5
)

$ErrorActionPreference = 'SilentlyContinue'

function Write-Light([string]$label, [bool]$ok, [string]$detail = '') {
  $emoji = if ($ok) { "🟢" } else { "🔴" }
  if ($detail) { Write-Host ("{0} {1} — {2}" -f $emoji, $label, $detail) }
  else { Write-Host ("{0} {1}" -f $emoji, $label) }
}

function Try-Invoke($url, $method = 'GET', $body = $null, $timeout = $TimeoutSec) {
  try {
    if ($method -eq 'GET') {
      $r = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec $timeout
    } else {
      $r = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec $timeout -Method $method -Body $body
    }
    return @{ ok = $true; code = $r.StatusCode; content = $r.Content }
  } catch {
    return @{ ok = $false; error = $_.Exception.Message }
  }
}

function Detect-Routes($base) {
  $d = Try-Invoke "$base/__debug"
  $result = @{ ok = $false; routes = @(); apiPath = $null; uiPath = $null; why = $null }
  if (-not $d.ok) { $result.why = $d.error; return $result }
  $lines = ($d.content -split "`r?`n")
  $routes = @()
  foreach($ln in $lines){ if ($ln -match '^\s*/') { $routes += ($ln -replace '\s','') } }
  $result.routes = $routes

  $apiCandidates = @('/api/watchdog','/api/api/watchdog')
  foreach ($p in $apiCandidates) { if ($routes -contains $p) { $result.apiPath = $p; break } }

  $uiCandidates = @('/app/watchdog','/app/app/watchdog')
  foreach ($p in $uiCandidates) { if ($routes -contains $p) { $result.uiPath = $p; break } }

  $result.ok = ($result.apiPath -or $result.uiPath)
  return $result
}

function Get-WatchdogPid() {
  $f = 'tmp\pid\watchdog.pid'
  if (Test-Path $f) {
    try { return [int](Get-Content $f -Raw).Trim() } catch { return $null }
  }
  return $null
}

function Is-ProcessAlive([int]$ProcId) {
  if (-not $ProcId) { return $false }
  $p = Get-Process -Id $ProcId -ErrorAction SilentlyContinue
  return [bool]$p
}

function Is-PortListening($port = 8776) {
  try {
    $c = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    return [bool]$c
  } catch { return $false }
}

function Get-LatestTunnelUrl() {
  $urls = @()

  $file = 'reports\ops\tunnel_url.txt'
  if (Test-Path $file) {
    $line = (Get-Content $file -TotalCount 1) -split '\s+'
    foreach ($u in $line) { if ($u -match 'https?://\S*trycloudflare\.com') { $urls += $u } }
  }

  foreach ($p in @('tmp\logs\cloudflared.err.log','tmp\logs\cloudflared.out.log')) {
    if (Test-Path $p) {
      $m = Select-String -Path $p -Pattern 'https?://\S*trycloudflare\.com' -AllMatches -ErrorAction SilentlyContinue
      if ($m) { $urls += ($m.Matches | ForEach-Object { $_.Value }) }
    }
  }

  $urls = $urls | Where-Object { $_ } | Select-Object -Unique
  if ($urls) { return $urls[-1] }
  return $null
}

function Restart-Watchdog() {
  try {
    pwsh tools\ps1\stop_watchdog.ps1 | Out-Null
    Start-Sleep -Milliseconds 600
    pwsh tools\ps1\run_watchdog.ps1 | Out-Null
    Start-Sleep -Seconds 2
    return $true
  } catch { return $false }
}

function Restart-Tunnel($base, $apiPath) {
  if (-not $apiPath) { return $null }
  $resp = Try-Invoke "$base$apiPath/tunnel/restart" 'POST' $null 10
  if (-not $resp.ok) { return $null }

  $deadline = (Get-Date).AddSeconds(60)
  $last = $null
  while ((Get-Date) -lt $deadline) {
    $u = Get-LatestTunnelUrl
    if ($u -and $u -ne $last) { return $u }
    $last = $u
    Start-Sleep -Milliseconds 700
  }
  return $null
}

function Save-PhoneUrl($url, $uiPath) {
  if (-not $url -or -not $uiPath) { return $null }
  $phone = "$url$uiPath"
  New-Item -ItemType Directory -Force 'reports\ops' | Out-Null
  Set-Content -Encoding UTF8 'reports\ops\tunnel_url.txt' $url
  Set-Content -Encoding UTF8 'reports\ops\phone_watchdog_url.txt' $phone
  return $phone
}

function Dump-Diag($snapshot) {
  try {
    New-Item -ItemType Directory -Force 'tmp\logs' | Out-Null
    $json = ($snapshot | ConvertTo-Json -Depth 6)
    Set-Content -Encoding UTF8 'tmp\logs\diag_status.json' $json

    $stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
    $zip = "tmp\logs\lights_dump_$stamp.zip"
    $toZip = @(
      'tmp\logs\diag_status.json',
      'tmp\logs\cloudflared.err.log',
      'tmp\logs\cloudflared.out.log',
      'tmp\logs\server.err.log',
      'tmp\logs\server.out.log',
      'reports\ops\watchdog_status.json',
      'reports\ops\tunnel_url.txt',
      'reports\ops\phone_watchdog_url.txt'
    ) | Where-Object { Test-Path $_ }

    if ($toZip) {
      if (Test-Path $zip) { Remove-Item $zip -Force }
      Compress-Archive -Path $toZip -DestinationPath $zip -Force
      return $zip
    }
  } catch {}
  return $null
}

function Open-Firewall8776 {
  try {
    $isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()
      ).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")
    if (-not $isAdmin) {
      return "Not admin; skip firewall rule."
    }
    if (-not (Get-Command New-NetFirewallRule -ErrorAction SilentlyContinue)) {
      return "Firewall cmdlets unavailable."
    }
    $rule = Get-NetFirewallRule -DisplayName "PA Watchdog 8776" -ErrorAction SilentlyContinue
    if ($rule) { return "Rule already exists." }
    New-NetFirewallRule -DisplayName "PA Watchdog 8776" -Direction Inbound -LocalPort 8776 -Protocol TCP -Action Allow -Profile Any | Out-Null
    return "Created firewall rule PA Watchdog 8776."
  } catch {
    return "Firewall rule error: $($_.Exception.Message)"
  }
}

function Run-Once([switch]$DoRepair) {
  $base = 'http://127.0.0.1:8776'
  $snapshot = [ordered]@{
    when    = (Get-Date).ToString('s')
    base    = $base
    lights  = [ordered]@{}
    details = [ordered]@{}
  }

  $wdp = Get-WatchdogPid
  $wdAlive = [bool](Is-ProcessAlive $wdp)
  $snapshot.lights.watchdog = $wdAlive
  $snapshot.details.watchdog_pid = $wdp
  $wdDetail = if ($wdp) { "PID $wdp" } else { "no pid file" }
  Write-Light "Watchdog running" $wdAlive $wdDetail

  $portOk = Is-PortListening 8776
  $snapshot.lights.port_8776 = $portOk
  Write-Light "Port 8776 listening" $portOk

  $h = Try-Invoke "$base/healthz"
  $healthOk = ($h.ok -and $h.code -eq 200)
  $snapshot.lights.healthz = $healthOk
  Write-Light "Healthz 200" $healthOk

  $routes = Detect-Routes $base
  $routesOk = $routes.ok
  $snapshot.lights.routes = $routesOk
  $snapshot.details.routes = $routes
  $routesDetail = if ($routesOk) { "api=$($routes.apiPath), ui=$($routes.uiPath)" } else { $routes.why }
  Write-Light "Routes mounted" $routesOk $routesDetail

  $apiOk = $false
  if ($routes.apiPath) {
    $apiResp = Try-Invoke "$base$($routes.apiPath)"
    $apiOk = ($apiResp.ok -and $apiResp.code -eq 200)
    $snapshot.details.api_probe = $apiResp
  }
  $snapshot.lights.api = $apiOk
  $apiDetail = if ($routes.apiPath) { $routes.apiPath } else { "no api route" }
  Write-Light "Watchdog API" $apiOk $apiDetail

  $uiOk = $false
  if ($routes.uiPath) {
    $uiResp = Try-Invoke "$base$($routes.uiPath)"
    $uiOk = ($uiResp.ok -and $uiResp.code -eq 200)
    $snapshot.details.ui_probe = @{ code = ($uiResp.code); ok = $uiResp.ok }
  }
  $snapshot.lights.ui = $uiOk
  $uiDetail = if ($routes.uiPath) { $routes.uiPath } else { "no ui route" }
  Write-Light "Watchdog UI" $uiOk $uiDetail

  $tunnel = Get-LatestTunnelUrl
  $snapshot.details.tunnel_url = $tunnel
  $snapshot.lights.tunnel_url = [bool]$tunnel
  Write-Light "Tunnel URL present" ([bool]$tunnel) ($tunnel if ($tunnel) else '')

  $extOk = $false
  if ($tunnel) {
    $ext = Try-Invoke "$tunnel/healthz"
    $extOk = ($ext.ok -and $ext.code -eq 200)
    $snapshot.details.tunnel_health = $ext
  }
  $snapshot.lights.external = $extOk
  Write-Light "External /healthz via tunnel" $extOk

  $phoneUrl = $null
  if ($tunnel -and $routes.uiPath) {
    $phoneUrl = Save-PhoneUrl $tunnel $routes.uiPath
    if ($phoneUrl) { Write-Host ("PHONE URL: {0}" -f $phoneUrl) }
  }

  if ($DoRepair) {
    $didSomething = $false
    if (-not ($portOk -and $healthOk)) {
      Write-Host "… Attempting watchdog restart"
      if (Restart-Watchdog) { $didSomething = $true }
      Start-Sleep -Seconds 2
      $portOk = Is-PortListening 8776
      $h2 = Try-Invoke "$base/healthz"
      $healthOk = ($h2.ok -and $h2.code -eq 200)
    }

    $routes = Detect-Routes $base
    if ($routes.apiPath -and (-not $tunnel -or -not $extOk)) {
      Write-Host "… Attempting tunnel restart via API"
      $newU = Restart-Tunnel $base $routes.apiPath
      if ($newU) {
        $tunnel = $newU
        $phoneUrl = Save-PhoneUrl $tunnel $routes.uiPath
        $didSomething = $true
      }
    }

    $fw = Open-Firewall8776
    if ($fw) { Write-Host $fw }

    if ($didSomething) {
      $extOk = $false
      if ($tunnel) {
        $ext2 = Try-Invoke "$tunnel/healthz"
        $extOk = ($ext2.ok -and $ext2.code -eq 200)
      }
    }
  }

  $snapshot.details.phone_url = $phoneUrl
  $zip = Dump-Diag $snapshot
  if ($zip) { Write-Host ("Saved diagnostics bundle: {0}" -f $zip) }

  $greens = ($snapshot.lights.GetEnumerator() | Where-Object { $_.Value } | Measure-Object).Count
  $total = ($snapshot.lights.Keys | Measure-Object).Count
  Write-Host ""
  Write-Host ("Summary: {0}/{1} green" -f $greens, $total)

  return $snapshot
}

if (-not (Test-Path 'tmp')) { New-Item -ItemType Directory -Force 'tmp' | Out-Null }
if (-not (Test-Path 'tmp\logs')) { New-Item -ItemType Directory -Force 'tmp\logs' | Out-Null }

if ($Watch) {
  Write-Host "Watching… (interval: $IntervalSeconds s) Ctrl+C to stop."
  while ($true) {
    Run-Once -DoRepair:$AutoRecover | Out-Null
    Start-Sleep -Seconds $IntervalSeconds
  }
} else {
  Run-Once -DoRepair:$AutoRecover | Out-Null
}
