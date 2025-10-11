param(
    [string] $UrlFile = 'reports\ops\tunnel_url.txt',
    [int]    $TimeoutSec = 15
)

function Get-TunnelUrl {
    if (Test-Path $UrlFile) {
        try { return (Get-Content $UrlFile -Raw).Trim() } catch {}
    }
    try {
        $m = Select-String -Path 'tmp\logs\cloudflared*.log' -AllMatches -Pattern 'https?://\S*trycloudflare\.com' -ErrorAction SilentlyContinue
        if ($m) { return ($m.Matches | ForEach-Object { $_.Value } | Select-Object -Last 1) }
    }
    catch {}
    return $null
}

# 1) resolve the URL
$u = Get-TunnelUrl
if (-not $u) { Write-Host "❌ No tunnel URL found. Start/refresh tunnel and try again." -ForegroundColor Red; exit 1 }

try { $uri = [Uri]$u } catch { Write-Host "❌ Bad URL: $u" -ForegroundColor Red; exit 1 }
$hostname = $uri.Host

Write-Host "Tunnel URL: $u"
Write-Host "Hostname  : $hostname"

# 2) DNS resolution
$dnsLocalOK = $false; $dnsLocalMsg = ""
$dns1111OK = $false; $dns1111Msg = ""

try {
    $r = Resolve-DnsName -Name $hostname -ErrorAction Stop
    $dnsLocalOK = $true
    $dnsLocalMsg = ($r | Where-Object { $_.IPAddress } | Select-Object -ExpandProperty IPAddress) -join ", "
}
catch { $dnsLocalMsg = $_.Exception.Message }

try {
    # Prefer Resolve-DnsName with -Server if available; fall back to nslookup
    $r2 = $null
    try { $r2 = Resolve-DnsName -Name $hostname -Server 1.1.1.1 -ErrorAction Stop } catch {}
    if ($r2) {
        $dns1111OK = $true
        $dns1111Msg = ($r2 | Where-Object { $_.IPAddress } | Select-Object -ExpandProperty IPAddress) -join ", "
    }
    else {
        $ns = nslookup $hostname 1.1.1.1 2>$null | Out-String
        $dns1111OK = ($ns -match 'Address:\s*\d+\.\d+\.\d+\.\d+' -or $ns -match 'Addresses:')
        $dns1111Msg = if ($dns1111OK) { 'OK via 1.1.1.1' } else { 'no A/AAAA from 1.1.1.1' }
    }
}
catch { $dns1111Msg = $_.Exception.Message }

Write-Host ("DNS (local resolver): {0}" -f ($(if ($dnsLocalOK) { "OK: $dnsLocalMsg" } else { "FAIL: $dnsLocalMsg" })))
Write-Host ("DNS (1.1.1.1)      : {0}" -f ($(if ($dns1111OK) { "OK: $dns1111Msg" } else { "FAIL: $dns1111Msg" })))

# 3) TCP 443 connectivity (only if local DNS worked)
$connectOK = $false; $connMsg = ""
if ($dnsLocalOK) {
    try {
        $connectOK = (Test-NetConnection -ComputerName $hostname -Port 443 -InformationLevel Quiet)
        $connMsg = if ($connectOK) { "OK" } else { "blocked" }
    }
    catch { $connMsg = $_.Exception.Message }
    Write-Host "TCP 443 reachability: $connMsg"
}
else {
    Write-Host "TCP 443 reachability: (skipped; local DNS failed)"
}

# 4) External /healthz probe
$extOK = $false; $extMsg = ""
try {
    $code = (Invoke-WebRequest ($u + "/healthz") -UseBasicParsing -TimeoutSec $TimeoutSec).StatusCode
    $extOK = ($code -eq 200)
    $extMsg = "HTTP $code"
}
catch { $extMsg = $_.Exception.Message }
Write-Host ("External /healthz   : {0}" -f ($(if ($extOK) { "OK (200)" } else { "FAIL ($extMsg)" })))

# 5) Classification
Write-Host ""
if (-not $dnsLocalOK -and -not $dns1111OK) {
    Write-Host "▶ RESULT: Tunnel hostname not resolvable (local & 1.1.1.1)." -ForegroundColor Yellow
    Write-Host "   Next: rotate the tunnel (new hostname) and retry:"
    Write-Host "     Get-Process cloudflared -ea SilentlyContinue | Stop-Process -Force"
    Write-Host "     cloudflared tunnel --no-autoupdate --protocol http2 --url http://127.0.0.1:8776"
    exit 2
}
if (-not $dnsLocalOK -and $dns1111OK) {
    Write-Host "▶ RESULT: Local DNS resolver is the problem." -ForegroundColor Yellow
    Write-Host "   Next: ipconfig /flushdns  (then retry)."
    Write-Host "         If it still fails, temporarily set adapter DNS to 1.1.1.1 or 8.8.8.8 and retry."
    exit 3
}
if ($dnsLocalOK -and -not $connectOK) {
    Write-Host "▶ RESULT: DNS OK, but outbound 443 appears blocked to Cloudflare edge." -ForegroundColor Yellow
    Write-Host "   Next: check local/firewall/security controls for outbound 443."
    exit 4
}
if ($dnsLocalOK -and $connectOK -and -not $extOK) {
    Write-Host "▶ RESULT: DNS & 443 OK; tunnel not serving yet (edge propagation/transient)." -ForegroundColor Yellow
    Write-Host "   Next: wait ~30–60s and retry. If still failing, rotate the tunnel (commands above)."
    exit 5
}
Write-Host "▶ RESULT: Everything looks good." -ForegroundColor Green
exit 0
