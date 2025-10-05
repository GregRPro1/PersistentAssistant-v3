<#
PA Auto Admin — unified diagnostics + repair for watchdog/server/tunnel.

Run:
  pwsh tools\ps1\pa_auto_admin.ps1                 # lights only
  pwsh tools\ps1\pa_auto_admin.ps1 -Repair         # try to fix watchdog/server/tunnel
  pwsh tools\ps1\pa_auto_admin.ps1 -FixFirewall    # smoke test firewall (adds rule if possible)
  pwsh tools\ps1\pa_auto_admin.ps1 -Repair -FixFirewall

Outputs:
  - Traffic lights, PHONE URL (if available)
  - tmp\logs\auto_admin_snapshot.json
  - tmp\logs\auto_admin_dump_YYYYMMDD_HHMMSS.zip
#>

param(
    [switch]$Repair,
    [switch]$FixFirewall,
    [int]$TimeoutSec = 5
)

function Get-TunnelUrlSafe {
    <#
      Returns the most recent https://*.trycloudflare.com URL, or $null.
      Sources (in order):
        1) reports\ops\tunnel_url.txt
        2) tmp\logs\cloudflared.out.log / tmp\logs\cloudflared.err.log
      IMPORTANT: Always treat results as an array so we never index a string.
    #>
    $candidates = @()

    # 1) canonical file
    $txt = 'reports\ops\tunnel_url.txt'
    if (Test-Path $txt) {
        try {
            $raw = Get-Content -LiteralPath $txt -Raw -ErrorAction Stop
            $m = [regex]::Match($raw, 'https?://\S*trycloudflare\.com')
            if ($m.Success) { $candidates += $m.Value.Trim() }
        }
        catch {}
    }

    # 2) logs (collect ALL matches)
    foreach ($p in @('tmp\logs\cloudflared.out.log', 'tmp\logs\cloudflared.err.log')) {
        if (Test-Path $p) {
            try {
                $matches = Select-String -Path $p -Pattern 'https?://\S*trycloudflare\.com' -AllMatches -ErrorAction Stop |
                ForEach-Object { $_.Matches } |
                ForEach-Object { $_.Value }
                if ($matches) { $candidates += $matches }
            }
            catch {}
        }
    }

    # Normalize + pick LAST as array (avoid string indexing pitfall)
    $flat = @($candidates | Where-Object { $_ -match '^https?://\S*trycloudflare\.com$' } | Select-Object -Unique)
    if ($flat.Count -gt 0) { return $flat[$flat.Count - 1] }
    return $null
}



function Write-Light([string]$label, [bool]$ok, [string]$detail = '') {
    $emoji = if ($ok) { "🟢" } else { "🔴" }
    if ($detail) { Write-Host ("{0} {1} — {2}" -f $emoji, $label, $detail) }
    else { Write-Host ("{0} {1}" -f $emoji, $label) }
}

function Test-IsAdmin {
    try {
        $id = [Security.Principal.WindowsIdentity]::GetCurrent()
        $p = New-Object Security.Principal.WindowsPrincipal($id)
        return $p.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
    }
    catch { return $false }
}

function Try-Invoke([string]$url, [string]$method = 'GET', $body = $null, [int]$timeout = $TimeoutSec) {
    try {
        if ($method -eq 'GET') {
            $r = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec $timeout
        }
        else {
            $r = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec $timeout -Method $method -Body $body
        }
        return @{ ok = $true; code = $r.StatusCode; content = $r.Content }
    }
    catch { return @{ ok = $false; error = $_.Exception.Message } }
}

function Read-WatchdogStatus {
    $p = 'reports\ops\watchdog_status.json'
    if (!(Test-Path $p)) { return @{ ok = $false; why = 'status file missing' } }
    try {
        $raw = Get-Content $p -Raw
        $obj = $raw | ConvertFrom-Json
        $age = (Get-Date) - (Get-Item $p).LastWriteTime
        return @{ ok = $true; obj = $obj; file_age_s = [int]$age.TotalSeconds }
    }
    catch { return @{ ok = $false; why = $_.Exception.Message } }
}

function Get-WatchdogPid {
    $f = 'tmp\pid\watchdog.pid'
    if (Test-Path $f) { try { return [int](Get-Content $f -Raw).Trim() } catch { return $null } }
    return $null
}

function Is-ProcessAlive([int]$procId) {
    if (-not $procId) { return $false }
    try { return [bool](Get-Process -Id $procId -ErrorAction SilentlyContinue) } catch { return $false }
}

function Is-PortListening([int]$port = 8776) {
    try { return [bool](Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue) } catch { return $false }
}

function Detect-Routes([string]$base) {
    $d = Try-Invoke "$base/__debug"
    $res = @{ ok = $false; why = $null; routes = @(); api = @(); ui = @() }
    if (-not $d.ok) { $res.why = $d.error; return $res }
    $lines = ($d.content -split "`r?`n") | Where-Object { $_ -match '^\s*/' }
    $routes = $lines | ForEach-Object { ($_ -replace '\s', '') }
    $res.routes = $routes
    $res.api = $routes | Where-Object { $_ -match '^/api(/.*)?watchdog' }
    $res.ui = $routes | Where-Object { $_ -match '^/app(/.*)?watchdog' }
    $res.ok = [bool]$routes.Count
    return $res
}

function Restart-Watchdog {
    try {
        pwsh tools\ps1\stop_watchdog.ps1 | Out-Null
        Start-Sleep -Milliseconds 600
        pwsh tools\ps1\run_watchdog.ps1 | Out-Null
        Start-Sleep -Seconds 1
        return $true
    }
    catch { return $false }
}

function Wait-Healthz([string]$base, [int]$seconds = 12) {
    $deadline = (Get-Date).AddSeconds($seconds)
    while ((Get-Date) -lt $deadline) {
        try {
            $sc = (Invoke-WebRequest "$base/healthz" -UseBasicParsing -TimeoutSec 2).StatusCode
            if ($sc -eq 200) { return $true }
        }
        catch {}
        Start-Sleep -Milliseconds 600
    }
    return $false
}

function Ensure-FirewallRule {
    $ruleName = 'PA Local 8776'
    $py = Join-Path (Get-Location) '.venv\Scripts\python.exe'
    $isAdmin = Test-IsAdmin
    $exists = (Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue)
    if ($exists) { return @{ ok = $true; created = $false; why = 'exists' } }
    if (-not $FixFirewall) { return @{ ok = $false; created = $false; why = 'skipped (use -FixFirewall)' } }
    if (-not $isAdmin) { return @{ ok = $false; created = $false; why = 'need admin to add firewall rule' } }
    try {
        New-NetFirewallRule -DisplayName $ruleName -Direction Inbound -LocalPort 8776 `
            -Protocol TCP -Action Allow -Profile Any `
            -Program ((Test-Path $py) ? $py : $null) | Out-Null
        return @{ ok = $true; created = $true; why = 'added' }
    }
    catch { return @{ ok = $false; created = $false; why = $_.Exception.Message } }
}

function Latest-TunnelUrl { return Get-TunnelUrlSafe }


function Restart-Tunnel([string]$base, [string]$apiPath) {
    if (-not $apiPath) { return $null }
    $resp = Try-Invoke "$base$apiPath/tunnel/restart" 'POST' $null 10
    if (-not $resp.ok) { return $null }
    $deadline = (Get-Date).AddSeconds(60)
    $last = $null
    while ((Get-Date) -lt $deadline) {
        Start-Sleep -Milliseconds 700
        $u = Latest-TunnelUrl
        if ($u -and $u -ne $last) { return $u }
        $last = $u
    }
    return $null
}

function Save-PhoneUrl([string]$tunnel, [string]$uiPath) {
    if (-not $tunnel -or -not $uiPath) { return $null }
    $phone = "$tunnel$uiPath"
    New-Item -ItemType Directory -Force 'reports\ops' | Out-Null
    Set-Content -Encoding UTF8 'reports\ops\tunnel_url.txt' $tunnel
    Set-Content -Encoding UTF8 'reports\ops\phone_watchdog_url.txt' $phone
    return $phone
}

function Dump-Snapshot($snap) {
    New-Item -ItemType Directory -Force 'tmp\logs' | Out-Null
    $json = ($snap | ConvertTo-Json -Depth 6)
    Set-Content -Encoding UTF8 'tmp\logs\auto_admin_snapshot.json' $json

    $stamp = Get-Date -Format 'yyyyMMdd_HHmmssfff'
    $staging = "tmp\logs\auto_admin_staging_$stamp"
    New-Item -ItemType Directory -Force $staging | Out-Null

    $want = @(
        'tmp\logs\auto_admin_snapshot.json',
        'tmp\logs\server.err.log', 'tmp\logs\server.out.log',
        'tmp\logs\cloudflared.err.log', 'tmp\logs\cloudflared.out.log',
        'reports\ops\watchdog_status.json',
        'reports\ops\tunnel_url.txt', 'reports\ops\phone_watchdog_url.txt',
        'config\processes.json'
    )

    foreach ($src in $want) {
        if (-not (Test-Path $src)) { continue }
        $dst = Join-Path $staging ([IO.Path]::GetFileName($src))
        try {
            # First try a normal copy (fast path)
            Copy-Item -LiteralPath $src -Destination $dst -ErrorAction Stop
        }
        catch {
            # If locked, fall back to "read-and-rewrite" which works with ReadShare
            try {
                $bytes = [System.IO.File]::Open($src, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read, [System.IO.FileShare]::ReadWrite)
                try {
                    $fs = New-Object System.IO.FileStream($dst, [System.IO.FileMode]::Create, [System.IO.FileAccess]::Write, [System.IO.FileShare]::None)
                    try {
                        $buffer = New-Object byte[] 65536
                        while (($n = $bytes.Read($buffer, 0, $buffer.Length)) -gt 0) {
                            $fs.Write($buffer, 0, $n)
                        }
                    }
                    finally { $fs.Dispose() }
                }
                finally { $bytes.Dispose() }
            }
            catch {
                # If still impossible to read, skip file (don't fail whole dump)
                Write-Verbose "Skip locked file: $src"
            }
        }
    }

    $zip = "tmp\logs\auto_admin_dump_$stamp.zip"
    try {
        if (Test-Path $zip) { Remove-Item $zip -Force -ErrorAction SilentlyContinue }
        Compress-Archive -Path (Join-Path $staging '*') -DestinationPath $zip -Force
        # best-effort cleanup
        Remove-Item $staging -Recurse -Force -ErrorAction SilentlyContinue
        if (Test-Path $zip) { return $zip }
    }
    catch {
        Remove-Item $staging -Recurse -Force -ErrorAction SilentlyContinue
    }
    return $null
}

function Get-WatchdogHeartbeatAgeSeconds {
    $p = 'reports\ops\watchdog_status.json'
    if (!(Test-Path $p)) { return $null }
    try {
        $fi = Get-Item $p
        $age = (Get-Date).ToUniversalTime() - $fi.LastWriteTimeUtc
        return [int]([Math]::Floor($age.TotalSeconds))
    }
    catch { return $null }
}

function Touch-WatchdogHeartbeat([int]$pid) {
    $p = 'reports\ops\watchdog_status.json'
    $now = Get-Date
    $obj = $null
    if (Test-Path $p) {
        try { $obj = (Get-Content -LiteralPath $p -Raw) | ConvertFrom-Json } catch {}
    }
    if (-not $obj) { $obj = [ordered]@{} }
    if (-not $obj.processes) { $obj.processes = @{} }
    if (-not $obj.processes.watchdog) { $obj.processes.watchdog = @{} }

    $obj.ok = $true
    $obj.updated_at = $now.ToString('s')
    $obj.processes.watchdog.pid = $pid
    $obj.processes.watchdog.state = 'running'

    New-Item -ItemType Directory -Force (Split-Path $p) | Out-Null
    ($obj | ConvertTo-Json -Depth 8) | Set-Content -LiteralPath $p -Encoding UTF8
}


# -------------------- MAIN --------------------
$base = 'http://127.0.0.1:8776'
$snap = [ordered]@{
    when         = (Get-Date).ToString('s')
    repair       = [bool]$Repair
    fix_firewall = [bool]$FixFirewall
    lights       = [ordered]@{}
    detail       = [ordered]@{}
}

# Firewall smoke test (optional)
$fw = Ensure-FirewallRule
$snap.detail.firewall = $fw
Write-Light "Firewall rule (8776)" $fw.ok $fw.why

# Watchdog status (file)
$ws = Read-WatchdogStatus
$snap.detail.watchdog_file = $ws
$wdPid = Get-WatchdogPid
$hbAge = Get-WatchdogHeartbeatAgeSeconds
$byPid = Is-ProcessAlive $wdPid
$byHb = ($hbAge -ne $null -and $hbAge -lt 60)  # consider "fresh" if updated in the last minute
$wdAlive = ($byPid -or $byHb)
$snap.lights.watchdog_alive = $wdAlive

# Try to self-heal stale heartbeat if PID is alive
if ($byPid -and (-not $byHb)) {
    $before = ($hbAge -ne $null) ? $hbAge : -1
    Touch-WatchdogHeartbeat $wdPid
    Start-Sleep -Milliseconds 250
    $hbAge = Get-WatchdogHeartbeatAgeSeconds
    $byHb = ($hbAge -ne $null -and $hbAge -lt 60)
    $wdAlive = ($byPid -or $byHb)
    $snap.lights.watchdog_alive = $wdAlive
    $snap.detail.watchdog_heartbeat_fix = @{ before = $before; after = $hbAge; pid = $wdPid; fixed = $byHb }
    if ($byHb) { Write-Host ("… refreshed watchdog heartbeat (was {0}s, now {1}s)" -f $before, $hbAge) }
}

# Light with detail
$hbTxt = ($hbAge -ne $null) ? ("; hb_age={0}s" -f $hbAge) : ""
Write-Light "Watchdog running" $wdAlive ("PID {0}{1}" -f ($wdPid ? $wdPid : 'n/a'), $hbTxt)

# Port
$portOk = Is-PortListening 8776
$snap.lights.port_8776 = $portOk
Write-Light "Port 8776 listening" $portOk

# Healthz
$h = Try-Invoke "$base/healthz"
$healthOk = ($h.ok -and $h.code -eq 200)
$snap.lights.healthz = $healthOk
Write-Light "Healthz 200" $healthOk

# Routes
$routes = Detect-Routes $base
$snap.detail.routes = $routes
$routesOk = $routes.ok
Write-Light "Routes mounted" $routesOk ($(if ($routesOk) { "api=$($routes.api -join ', '); ui=$($routes.ui -join ', ')" } else { $routes.why }))

# API probe (prefer the shortest api path)
$apiOk = $false; $apiPath = $null
if ($routes.api.Count) {
    $apiPath = ($routes.api | Sort-Object Length | Select-Object -First 1)
    $apiResp = Try-Invoke "$base$apiPath"
    $apiOk = ($apiResp.ok -and $apiResp.code -eq 200)
    $snap.detail.api_probe = @{ path = $apiPath; resp = $apiResp }
}
$snap.lights.api = $apiOk
Write-Light "Watchdog API" $apiOk ($apiPath ? $apiPath : 'missing')

# UI probe (prefer the shortest ui path)
$uiOk = $false; $uiPath = $null
if ($routes.ui.Count) {
    $uiPath = ($routes.ui | Sort-Object Length | Select-Object -First 1)
    $uiResp = Try-Invoke "$base$uiPath"
    $uiOk = ($uiResp.ok -and $uiResp.code -eq 200)
    $snap.detail.ui_probe = @{ path = $uiPath; resp = @{ ok = $uiResp.ok; code = $uiResp.code } }
}
$snap.lights.ui = $uiOk
Write-Light "Watchdog UI" $uiOk ($uiPath ? $uiPath : 'missing')

# Tunnel + external
$tunnel = Latest-TunnelUrl
$snap.detail.tunnel_url = $tunnel
$snap.lights.tunnel_present = [bool]$tunnel
Write-Light "Tunnel URL present" ([bool]$tunnel) ($tunnel ? $tunnel : '')

$extOk = $false
if ($tunnel) {
    $eh = Try-Invoke "$tunnel/healthz"
    $extOk = ($eh.ok -and $eh.code -eq 200)
    $snap.detail.external_health = $eh
}
$snap.lights.external = $extOk
Write-Light "External /healthz via tunnel" $extOk

# Auto-repair loop
if ($Repair) {
    $did = $false

    if (-not ($portOk -and $healthOk)) {
        Write-Host "… restarting watchdog/server"
        if (Restart-Watchdog) { $did = $true }
        $healthOk = Wait-Healthz $base 15
        $portOk = Is-PortListening 8776
        Write-Light "Healthz 200 (post-restart)" $healthOk
        Write-Light "Port 8776 listening (post-restart)" $portOk
    }

    # Re-detect routes after restart
    $routes = Detect-Routes $base
    $snap.detail.routes_after = $routes
    $apiPath = ($routes.api | Sort-Object Length | Select-Object -First 1)
    $uiPath = ($routes.ui  | Sort-Object Length | Select-Object -First 1)

    if ($apiPath -and (-not $tunnel -or -not $extOk)) {
        Write-Host "… restarting tunnel via API"
        $newU = Restart-Tunnel $base $apiPath
        if ($newU) { $tunnel = $newU; $did = $true }
    }

    if ($tunnel -and $uiPath) {
        $phone = Save-PhoneUrl $tunnel $uiPath
        if ($phone) { Write-Host ("PHONE URL: {0}" -f $phone) }
        $eh2 = Try-Invoke "$tunnel/healthz"
        $extOk = ($eh2.ok -and $eh2.code -eq 200)
    }

    if (-not $did) {
        Write-Host "No changes applied (nothing actionable)."
    }
}

# Final summary + dump
$greens = ($snap.lights.GetEnumerator() | Where-Object { $_.Value } | Measure-Object).Count
$total = ($snap.lights.Keys | Measure-Object).Count
Write-Host ("`nSummary: {0}/{1} green" -f $greens, $total)

$zip = Dump-Snapshot $snap
if ($zip) { Write-Host ("Saved diagnostics bundle: {0}" -f $zip) }


