# tools\ps1\pa_lights.ps1
# Traffic-light diagnostics + optional auto-repair for PA server and Cloudflare quick tunnel.
# Usage:
#   pwsh tools\ps1\pa_lights.ps1
#   pwsh tools\ps1\pa_lights.ps1 -Repair
#   pwsh tools\ps1\pa_lights.ps1 -Watch -IntervalSeconds 10 -Repair

param(
    [switch]$Repair,
    [switch]$Watch,
    [int]$IntervalSeconds = 10,
    [int]$TimeoutSec = 5
)

# --- Helpers -----------------------------------------------------------------

function Write-Light([string]$label, [bool]$ok, [string]$detail = '') {
    $emoji = if ($ok) { "🟢" } else { "🔴" }
    if ($detail) {
        Write-Host ("{0} {1} — {2}" -f $emoji, $label, $detail)
    }
    else {
        Write-Host ("{0} {1}" -f $emoji, $label)
    }
}

function Try-Invoke($url, $method = 'GET', $body = $null, $timeout = $TimeoutSec) {
    try {
        if ($method -eq 'GET') {
            $r = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec $timeout
        }
        else {
            $r = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec $timeout -Method $method -Body $body
        }
        return @{ ok = $true; code = $r.StatusCode; content = $r.Content }
    }
    catch {
        return @{ ok = $false; error = $_.Exception.Message }
    }
}

function Detect-Routes($base) {
    $d = Try-Invoke "$base/__debug"
    $result = @{ ok = $false; routes = @(); apiPath = $null; uiPath = $null; why = $null }
    if (-not $d.ok) { $result.why = $d.error; return $result }
    $lines = ($d.content -split "`r?`n")
    $routes = $lines | Where-Object { $_ -match '^\s*/' } | ForEach-Object { ($_ -replace '\s', '') }
    $result.routes = $routes

    $apiCandidates = @('/api/api/watchdog', '/api/watchdog')
    foreach ($p in $apiCandidates) { if ($routes -contains $p) { $result.apiPath = $p; break } }

    $uiCandidates = @('/app/app/watchdog', '/app/watchdog')
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

function Is-ProcessAlive([int]$procId) {
    if (-not $procId) { return $false }
    $p = Get-Process -Id $procId -ErrorAction SilentlyContinue
    return [bool]$p
}

function Is-PortListening($port = 8776) {
    try {
        $c = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
        return [bool]$c
    }
    catch { return $false }
}

function Get-LatestTunnelUrl() {
    $urls = @()

    # canonical file
    $file = 'reports\ops\tunnel_url.txt'
    if (Test-Path $file) {
        $line = (Get-Content $file -TotalCount 1) -split '\s+'
        foreach ($u in $line) { if ($u -match 'https?://\S*trycloudflare\.com') { $urls += $u } }
    }

    # logs
    foreach ($p in @('tmp\logs\cloudflared.err.log', 'tmp\logs\cloudflared.out.log')) {
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
        pwsh tools\ps1\run_watchdog.ps1    | Out-Null
        Start-Sleep -Seconds 2
        return $true
    }
    catch { return $false }
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
        $path = 'tmp\logs\diag_status.json'
        Set-Content -Encoding UTF8 $path $json

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
    }
    catch { }
    return $null
}

# --- Main check/repair loop ---------------------------------------------------

function Run-Once([switch]$DoRepair) {
    $base = 'http://127.0.0.1:8776'
    $snapshot = [ordered]@{
        when    = (Get-Date).ToString('s')
        base    = $base
        lights  = [ordered]@{}
        details = [ordered]@{}
    }

    # Watchdog
    $wdp = Get-WatchdogPid
    $wdAlive = [bool](Is-ProcessAlive $wdp)
    $snapshot.lights.watchdog = $wdAlive
    $snapshot.details.watchdog_pid = $wdp
    Write-Light "Watchdog running" $wdAlive ("PID {0}" -f ($wdp ?? 'n/a'))

    # Port 8776
    $portOk = Is-PortListening 8776
    $snapshot.lights.port_8776 = $portOk
    Write-Light "Port 8776 listening" $portOk

    # Healthz
    $h = Try-Invoke "$base/healthz"
    $healthOk = ($h.ok -and $h.code -eq 200)
    $snapshot.lights.healthz = $healthOk
    Write-Light "Healthz 200" $healthOk

    # Routes
    $routes = Detect-Routes $base
    $routesOk = $routes.ok
    $snapshot.lights.routes = $routesOk
    $snapshot.details.routes = $routes
    $routesDetail = if ($routesOk) { "api=$($routes.apiPath), ui=$($routes.uiPath)" } else { $routes.why }
Write-Light "Routes mounted" $routesOk $routesDetail

    # API
    $apiOk = $false
    if ($routes.apiPath) {
        $apiResp = Try-Invoke "$base$($routes.apiPath)"
        $apiOk = ($apiResp.ok -and $apiResp.code -eq 200)
        $snapshot.details.api_probe = $apiResp
    }
    $snapshot.lights.api = $apiOk
    $apiDetail = if ($routes.apiPath) { $routes.apiPath } else { "no api route" }
Write-Light "Watchdog API" $apiOk $apiDetail

    # UI
    $uiOk = $false
    if ($routes.uiPath) {
        $uiResp = Try-Invoke "$base$($routes.uiPath)"
        $uiOk = ($uiResp.ok -and $uiResp.code -eq 200)
        $snapshot.details.ui_probe = @{ code = ($uiResp.code); ok = $uiResp.ok }
    }
    $snapshot.lights.ui = $uiOk
    $uiDetail = if ($routes.uiPath) { $routes.uiPath } else { "no ui route" }
Write-Light "Watchdog UI" $uiOk $uiDetail

    # Tunnel URL (local)
    $tunnel = Get-LatestTunnelUrl
    $snapshot.details.tunnel_url = $tunnel
    $snapshot.lights.tunnel_url = [bool]$tunnel
    Write-Light "Tunnel URL present" ([bool]$tunnel) ($tunnel ?? '')

    # External reachability via tunnel
    $extOk = $false
    if ($tunnel) {
        $ext = Try-Invoke "$tunnel/healthz"
        $extOk = ($ext.ok -and $ext.code -eq 200)
        $snapshot.details.tunnel_health = $ext
    }
    $snapshot.lights.external = $extOk
    Write-Light "External /healthz via tunnel" $extOk

    # Phone URL file (if possible)
    $phoneUrl = $null
    if ($tunnel -and $routes.uiPath) {
        $phoneUrl = Save-PhoneUrl $tunnel $routes.uiPath
        if ($phoneUrl) { Write-Host ("PHONE URL: {0}" -f $phoneUrl) }
    }

    # Attempt repairs if requested
    if ($DoRepair) {
        $didSomething = $false

        if (-not ($portOk -and $healthOk)) {
            Write-Host "… Attempting watchdog restart"
            if (Restart-Watchdog) { $didSomething = $true }
            Start-Sleep -Seconds 2
            # Re-check basics quickly
            $portOk = Is-PortListening 8776
            $h2 = Try-Invoke "$base/healthz"
            $healthOk = ($h2.ok -and $h2.code -eq 200)
        }

        # Re-detect routes after potential restart
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

        if ($didSomething) {
            # Final quick probe
            $extOk = $false
            if ($tunnel) {
                $ext2 = Try-Invoke "$tunnel/healthz"
                $extOk = ($ext2.ok -and $ext2.code -eq 200)
            }
        }
    }

    # Finalize snapshot and dump
    $snapshot.details.phone_url = $phoneUrl
    $zip = Dump-Diag $snapshot
    if ($zip) { Write-Host ("Saved diagnostics bundle: {0}" -f $zip) }

    # Summary line for quick glance
    $greens = ($snapshot.lights.GetEnumerator() | Where-Object { $_.Value } | Measure-Object).Count
    $total = ($snapshot.lights.Keys | Measure-Object).Count
    Write-Host ""
    Write-Host ("Summary: {0}/{1} green" -f $greens, $total)

    return $snapshot
}

# --- Driver -------------------------------------------------------------------

if (-not (Test-Path 'tmp')) { New-Item -ItemType Directory -Force 'tmp' | Out-Null }
if (-not (Test-Path 'tmp\logs')) { New-Item -ItemType Directory -Force 'tmp\logs' | Out-Null }

if ($Watch) {
    Write-Host "Watching… (interval: $IntervalSeconds s) Ctrl+C to stop."
    while ($true) {
        Run-Once -DoRepair:$Repair | Out-Null
        Start-Sleep -Seconds $IntervalSeconds
    }
}
else {
    Run-Once -DoRepair:$Repair | Out-Null
}

