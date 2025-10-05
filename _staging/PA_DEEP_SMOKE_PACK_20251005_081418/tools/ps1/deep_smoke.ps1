# tools\ps1\deep_smoke.ps1
# Deep Smoke: end-to-end diagnostics + optional recovery for PA server & Cloudflare tunnel.
# Usage:
#   pwsh tools\ps1\deep_smoke.ps1
#   pwsh tools\ps1\deep_smoke.ps1 -Restart

param(
    [switch]$Restart,
    [int]$TimeoutSec = 5,
    [int]$WaitAfterRestartSec = 3
)

# ---------------- Helpers ----------------

function Write-Light([string]$label, [bool]$ok, [string]$detail = ''){
    $emoji = if ($ok) { '🟢' } else { '🔴' }
    if ($detail) {
        Write-Host ("{0} {1} — {2}" -f $emoji, $label, $detail)
    } else {
        Write-Host ("{0} {1}" -f $emoji, $label)
    }
}

function Try-Invoke([string]$url, [string]$method = 'GET', $body = $null, [int]$timeout = 5){
    try {
        if ($method -eq 'GET') {
            $r = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec $timeout
        } else {
            $r = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec $timeout -Method $method -Body $body
        }
        return @{ ok=$true; code=$r.StatusCode; content=$r.Content }
    } catch {
        return @{ ok=$false; error=$_.Exception.Message }
    }
}

function Is-PortListening([int]$port){
    try {
        $c = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
        return [bool]$c
    } catch { return $false }
}

function Get-WatchdogPid(){
    $f = 'tmp\pid\watchdog.pid'
    if (Test-Path $f){
        try { return [int](Get-Content -Raw $f).Trim() } catch { return $null }
    }
    return $null
}

function Is-ProcessAlive([int]$procId){
    if (-not $procId) { return $false }
    $p = Get-Process -Id $procId -ErrorAction SilentlyContinue
    return [bool]$p
}

function Detect-Routes([string]$base){
    $d = Try-Invoke "$base/__debug" 'GET' $null $TimeoutSec
    $result = @{ ok=$false; routes=@(); apiPath=$null; uiPath=$null; why=$null }
    if (-not $d.ok){ $result.why = $d.error; return $result }
    $lines = ($d.content -split "`r?`n")
    $routes = @()
    foreach($ln in $lines){
        if ($ln -match '^\s*/'){ $routes += ($ln -replace '\s','') }
    }
    $result.routes = $routes
    foreach($p in @('/api/watchdog','/api/api/watchdog')){ if ($routes -contains $p){ $result.apiPath = $p; break } }
    foreach($p in @('/app/watchdog','/app/app/watchdog')){ if ($routes -contains $p){ $result.uiPath  = $p; break } }
    $result.ok = [bool]($result.apiPath -or $result.uiPath)
    return $result
}

function Get-LatestTunnelUrl(){
    $urls = @()
    $canon = 'reports\ops\tunnel_url.txt'
    if (Test-Path $canon){
        $line = (Get-Content $canon -TotalCount 1) -split '\s+'
        foreach($u in $line){ if ($u -match 'https?://\S*trycloudflare\.com'){ $urls += $u } }
    }
    foreach($p in @('tmp\logs\cloudflared.err.log','tmp\logs\cloudflared.out.log')){
        if (Test-Path $p){
            $m = Select-String -Path $p -Pattern 'https?://\S*trycloudflare\.com' -AllMatches -ErrorAction SilentlyContinue
            if ($m){ $urls += ($m.Matches | ForEach-Object { $_.Value }) }
        }
    }
    $urls = $urls | Where-Object { $_ } | Select-Object -Unique
    if ($urls){ return $urls[-1] }
    return $null
}

function Save-PhoneUrl([string]$tunnel,[string]$uiPath){
    if (-not $tunnel -or -not $uiPath){ return $null }
    $phone = "$tunnel$uiPath"
    New-Item -ItemType Directory -Force 'reports\ops' | Out-Null
    Set-Content -Path 'reports\ops\tunnel_url.txt' -Value $tunnel -Encoding UTF8
    Set-Content -Path 'reports\ops\phone_watchdog_url.txt' -Value $phone -Encoding UTF8
    return $phone
}

function Restart-Watchdog(){
    try {
        pwsh -NoProfile -ExecutionPolicy Bypass -File 'tools\ps1\stop_watchdog.ps1' | Out-Null
        Start-Sleep -Milliseconds 700
        pwsh -NoProfile -ExecutionPolicy Bypass -File 'tools\ps1\run_watchdog.ps1'  | Out-Null
        Start-Sleep -Seconds $WaitAfterRestartSec
        return $true
    } catch { return $false }
}

function Restart-Tunnel([string]$base,[string]$apiPath){
    if (-not $apiPath){ return $null }
    $resp = Try-Invoke ("{0}{1}/tunnel/restart" -f $base,$apiPath) 'POST' $null 10
    if (-not $resp.ok){ return $null }
    $deadline = (Get-Date).AddSeconds(60)
    $last = $null
    while((Get-Date) -lt $deadline){
        $u = Get-LatestTunnelUrl
        if ($u -and $u -ne $last){ return $u }
        $last = $u
        Start-Sleep -Milliseconds 700
    }
    return $null
}

function Dump-DoublePrefixReport(){
    $targets = @('server','server\*.py','server\**\*.py')
    $hits = @()
    foreach($pattern in $targets){
        Get-ChildItem -Path $pattern -File -Recurse -ErrorAction SilentlyContinue | ForEach-Object {
            $p = $_.FullName
            try {
                $i = 0
                Get-Content -LiteralPath $p | ForEach-Object {
                    $i++
                    $line = $_
                    if ($line -match '/api/api' -or $line -match '/app/app' -or $line -match 'url_prefix\s*=\s*["'']/(api|app)'){
                        $hits += [pscustomobject]@{ file=$p; line=$i; text=$line }
                    }
                }
            } catch { }
        }
    }
    $out = @{ hits=$hits; when=(Get-Date).ToString('s') }
    New-Item -ItemType Directory -Force 'tmp\logs' | Out-Null
    $path = 'tmp\logs\double_prefix_report.json'
    ($out | ConvertTo-Json -Depth 6) | Set-Content -Path $path -Encoding UTF8
    return $path
}

function Dump-ModuleFootprint(){
    $py = $null
    $cand = @('.venv\Scripts\python.exe','python.exe','python')
    foreach($c in $cand){ if (Get-Command $c -ErrorAction SilentlyContinue){ $py = $c; break } }
    if (-not $py){ return $null }

    $probe = @"
import importlib, json
mods = ["server.bootstrap_mounts","server.watchdog_api","server.watchdog_ui","server.mobile_home","server.ops_pages","server.control_console","pa_lan","serve_phone_lan"]
out = {}
for m in mods:
    try:
        mod = importlib.import_module(m)
        out[m] = {"ok": True, "file": getattr(mod, "__file__", None)}
    except Exception as e:
        out[m] = {"ok": False, "error": str(e)}
print(json.dumps(out))
"@

    New-Item -ItemType Directory -Force 'tmp\logs' | Out-Null
    $tmpPy = Join-Path 'tmp\logs' 'module_probe.py'
    Set-Content -Path $tmpPy -Value $probe -Encoding UTF8

    try {
        $json = & $py $tmpPy
        $path = 'tmp\logs\module_paths.json'
        Set-Content -Path $path -Value $json -Encoding UTF8
        return $path
    } catch { return $null }
}

function Save-Bundle($paths){
    $paths = $paths | Where-Object { $_ -and (Test-Path $_) } | Select-Object -Unique
    if (-not $paths){ return $null }
    $stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
    $zip = "tmp\logs\deep_smoke_dump_$stamp.zip"
    try {
        if (Test-Path $zip){ Remove-Item $zip -Force }
        Compress-Archive -Path $paths -DestinationPath $zip -Force
        return $zip
    } catch { return $null }
}

# --------------- Main ---------------

if (-not (Test-Path 'tmp')) { New-Item -ItemType Directory -Force 'tmp' | Out-Null }
if (-not (Test-Path 'tmp\logs')) { New-Item -ItemType Directory -Force 'tmp\logs' | Out-Null }

$base = 'http://127.0.0.1:8776'
$report = [ordered]@{
    when = (Get-Date).ToString('s')
    base = $base
    lights = [ordered]@{}
    details = [ordered]@{}
}

# A) module footprint + duplication scan (non-blocking)
$modPath = Dump-ModuleFootprint
$dupPath = Dump-DoublePrefixReport
$report.details.module_paths_json = $modPath
$report.details.double_prefix_json = $dupPath

# B) basic service checks
$wdPid   = Get-WatchdogPid
$wdAlive = Is-ProcessAlive $wdPid
$report.lights.watchdog = $wdAlive
$report.details.watchdog_pid = $wdPid
$wdDetail = ($wdPid -as [string]); if (-not $wdDetail){ $wdDetail = 'n/a' }
Write-Light "Watchdog running" $wdAlive ("PID {0}" -f $wdDetail)

$portOk = Is-PortListening 8776
$report.lights.port_8776 = $portOk
Write-Light "Port 8776 listening" $portOk

$h = Try-Invoke "$base/healthz" 'GET' $null $TimeoutSec
$healthOk = ($h.ok -and $h.code -eq 200)
$report.lights.healthz = $healthOk
Write-Light "Healthz 200" $healthOk

$routes    = Detect-Routes $base
$routesOk  = $routes.ok
$report.lights.routes = $routesOk
$report.details.routes = $routes
$routesDetail = if ($routesOk) { "api=$($routes.apiPath), ui=$($routes.uiPath)" } else { $routes.why }
Write-Light "Routes mounted" $routesOk $routesDetail

$apiOk = $false
if ($routes.apiPath){
    $apiResp = Try-Invoke ("{0}{1}" -f $base,$routes.apiPath) 'GET' $null $TimeoutSec
    $apiOk = ($apiResp.ok -and $apiResp.code -eq 200)
    $report.details.api_probe = $apiResp
}
$report.lights.api = $apiOk
$apiDetail = if ($routes.apiPath){ $routes.apiPath } else { 'no api route' }
Write-Light "Watchdog API" $apiOk $apiDetail

$uiOk = $false
if ($routes.uiPath){
    $uiResp = Try-Invoke ("{0}{1}" -f $base,$routes.uiPath) 'GET' $null $TimeoutSec
    $uiOk = ($uiResp.ok -and $uiResp.code -eq 200)
    $report.details.ui_probe = $uiResp
}
$report.lights.ui = $uiOk
$uiDetail = if ($routes.uiPath){ $routes.uiPath } else { 'no ui route' }
Write-Light "Watchdog UI" $uiOk $uiDetail

$tunnel = Get-LatestTunnelUrl
$report.details.tunnel_url = $tunnel
$report.lights.tunnel_url = [bool]$tunnel
$tunnelDetail = if ($tunnel){ $tunnel } else { '' }
Write-Light "Tunnel URL present" ([bool]$tunnel) $tunnelDetail

$extOk = $false
if ($tunnel){
    $ext = Try-Invoke ("{0}/healthz" -f $tunnel) 'GET' $null 10
    $extOk = ($ext.ok -and $ext.code -eq 200)
    $report.details.tunnel_health = $ext
}
$report.lights.external = $extOk
Write-Light "External /healthz via tunnel" $extOk

$phoneUrl = $null
if ($tunnel -and $routes.uiPath){
    $phoneUrl = Save-PhoneUrl $tunnel $routes.uiPath
    if ($phoneUrl){ Write-Host ("PHONE URL: {0}" -f $phoneUrl) }
}
$report.details.phone_url = $phoneUrl

# C) optional recovery attempts
if ($Restart){
    $did = $false
    if (-not ($portOk -and $healthOk)){
        Write-Host "… Attempting watchdog restart"
        if (Restart-Watchdog){ $did = $true }
        $h = Try-Invoke "$base/healthz" 'GET' $null $TimeoutSec
        $healthOk = ($h.ok -and $h.code -eq 200)
    }
    $routes = Detect-Routes $base
    if ($routes.apiPath -and (-not $tunnel -or -not $extOk)){
        Write-Host "… Attempting tunnel restart via API"
        $newU = Restart-Tunnel $base $routes.apiPath
        if ($newU){
            $tunnel = $newU
            $phoneUrl = Save-PhoneUrl $tunnel $routes.uiPath
            $ext = Try-Invoke ("{0}/healthz" -f $tunnel) 'GET' $null 10
            $extOk = ($ext.ok -and $ext.code -eq 200)
            $did = $true
        }
    }
    if ($did){
        $report.details.tunnel_url = $tunnel
        $report.details.phone_url = $phoneUrl
        $report.lights.external = $extOk
    }
}

# D) write report + bundle
New-Item -ItemType Directory -Force 'tmp\logs' | Out-Null
$repPath = 'tmp\logs\deep_smoke_report.json'
($report | ConvertTo-Json -Depth 6) | Set-Content -Path $repPath -Encoding UTF8

$bundle = Save-Bundle @(
    $repPath,
    'tmp\logs\double_prefix_report.json',
    'tmp\logs\module_paths.json',
    'tmp\logs\cloudflared.err.log',
    'tmp\logs\cloudflared.out.log',
    'tmp\logs\server.err.log',
    'tmp\logs\server.out.log',
    'reports\ops\watchdog_status.json',
    'reports\ops\tunnel_url.txt',
    'reports\ops\phone_watchdog_url.txt'
)

$greens = ($report.lights.GetEnumerator() | Where-Object { $_.Value } | Measure-Object).Count
$total  = ($report.lights.Keys | Measure-Object).Count
Write-Host ""
Write-Host ("Summary: {0}/{1} green" -f $greens, $total)
if ($bundle){ Write-Host ("Saved diagnostics bundle: {0}" -f $bundle) }
