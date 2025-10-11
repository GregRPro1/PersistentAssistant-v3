# tools\ps1\watchdog_core.ps1
param()

$ErrorActionPreference = 'Stop'

function Ensure-Dir($p) { if (-not (Test-Path $p)) { New-Item -ItemType Directory -Force $p | Out-Null } }

# Resolve repo root from this script's location
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = Split-Path -Parent $Here     # ...\tools
$Root = Split-Path -Parent $Root     # repo root

# Canonical files
$PidDir = Join-Path $Root 'tmp\pid'
$LogsDir = Join-Path $Root 'tmp\logs'
$OpsDir = Join-Path $Root 'reports\ops'
$Status = Join-Path $OpsDir 'watchdog_status.json'

Ensure-Dir $PidDir
Ensure-Dir $LogsDir
Ensure-Dir $OpsDir

# Write our PID for stop_watchdog.ps1
$SelfPid = $PID
Set-Content -LiteralPath (Join-Path $PidDir 'watchdog.pid') -Value $SelfPid -Encoding ascii

function Get-LocalHealth() {
    $base = 'http://127.0.0.1:8776'
    $health = @{ ok = $false; code = 0; err = $null }
    try {
        $r = Invoke-WebRequest -Uri "$base/healthz" -UseBasicParsing -TimeoutSec 2
        $health.ok = ($r.StatusCode -eq 200)
        $health.code = $r.StatusCode
    }
    catch {
        $health.err = $_.Exception.Message
    }
    return $health
}

function Is-PortListening([int]$port = 8776) {
    try { return [bool](Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue) }
    catch { return $false }
}

function Get-TunnelUrl() {
    $txt = Join-Path $OpsDir 'tunnel_url.txt'
    if (Test-Path $txt) {
        try {
            $raw = Get-Content -LiteralPath $txt -Raw
            $m = [regex]::Match($raw, 'https?://\S*trycloudflare\.com')
            if ($m.Success) { return $m.Value.Trim() }
        }
        catch {}
    }
    foreach ($p in @('cloudflared.out.log', 'cloudflared.err.log')) {
        $full = Join-Path $LogsDir $p
        if (Test-Path $full) {
            try {
                $last = Select-String -Path $full -Pattern 'https?://\S*trycloudflare\.com' -AllMatches |
                ForEach-Object { $_.Matches.Value } | Select-Object -Last 1
                if ($last) { return $last.Trim() }
            }
            catch {}
        }
    }
    return $null
}

# Main loop: refresh heartbeat
while ($true) {
    try {
        $now = Get-Date
        $health = Get-LocalHealth
        $portUp = Is-PortListening 8776
        $tunnel = Get-TunnelUrl

        # Build status document
        $doc = [ordered]@{
            ok         = $health.ok -and $portUp
            updated_at = $now.ToString('s')
            processes  = [ordered]@{
                watchdog = @{
                    pid   = $SelfPid
                    state = 'running'
                }
                server   = @{
                    port_8776 = $portUp
                    healthz   = $health
                }
                tunnel   = @{
                    url   = $tunnel
                    state = ($tunnel ? 'healthy' : 'unknown')
                }
            }
        }

        ($doc | ConvertTo-Json -Depth 10) | Set-Content -LiteralPath $Status -Encoding UTF8
    }
    catch {
        # Best-effort: still update a minimal heartbeat so consumers see activity
        try {
            $mini = @{ ok = $false; updated_at = (Get-Date).ToString('s'); error = $_.Exception.Message; processes = @{watchdog = @{pid = $SelfPid; state = 'degraded' } } }
            ($mini | ConvertTo-Json -Depth 6) | Set-Content -LiteralPath $Status -Encoding UTF8
        }
        catch {}
    }

    Start-Sleep -Seconds 5
}
