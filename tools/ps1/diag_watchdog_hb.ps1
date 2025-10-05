# tools\ps1\diag_watchdog_hb.ps1  (fixed)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Continue'

$root = Get-Location
$status = Join-Path $root 'reports\ops\watchdog_status.json'
$pidf = Join-Path $root 'tmp\pid\watchdog.pid'

Write-Host "Repo: $root"
Write-Host "Status file: $status"

if (Test-Path $status) {
    $fi = Get-Item $status
    Write-Host ("Before: LastWriteTime = {0}" -f $fi.LastWriteTime)
}
else {
    Write-Host "Before: (no file)"
}

$wdPid = $null
if (Test-Path $pidf) {
    try { $wdPid = [int]((Get-Content $pidf -Raw).Trim()) } catch {}
}
$wdAlive = $false
if ($wdPid) { $wdAlive = [bool](Get-Process -Id $wdPid -ErrorAction SilentlyContinue) }
Write-Host ("Watchdog PID: {0} (alive={1})" -f ($wdPid ? $wdPid : 'n/a'), $wdAlive)

function Write-JsonAtomic([string]$path, [string]$json) {
    $dir = Split-Path $path -Parent
    if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }
    $tmp = "$path.tmp"
    try {
        $fs = [System.IO.FileStream]::new($tmp, [System.IO.FileMode]::Create, [System.IO.FileAccess]::Write, [System.IO.FileShare]::Read)
        $sw = New-Object System.IO.StreamWriter($fs, [System.Text.Encoding]::UTF8)
        $sw.Write($json); $sw.Flush(); $sw.Dispose(); $fs.Dispose()
        Move-Item -LiteralPath $tmp -Destination $path -Force
        return $true
    }
    catch {
        if (Test-Path $tmp) { Remove-Item $tmp -Force -ErrorAction SilentlyContinue }
        Write-Error ("Atomic write failed: {0}" -f $_.Exception.Message)
        return $false
    }
}

# build/update a minimal status payload
$now = Get-Date
$obj = [ordered]@{
    ok         = $true
    updated_at = $now.ToString('s')
    processes  = [ordered]@{
        watchdog = @{ pid = $wdPid; state = ($wdAlive ? 'running' : 'unknown') }
    }
}
$json = $obj | ConvertTo-Json -Depth 8
$ok = Write-JsonAtomic $status $json
Write-Host ("Write attempt: {0}" -f ($ok ? "OK" : "FAIL"))

if (Test-Path $status) {
    $fi = Get-Item $status
    Write-Host ("After: LastWriteTime  = {0}" -f $fi.LastWriteTime)
    $u = (Get-Content $status -Raw | ConvertFrom-Json).updated_at
    Write-Host ("After: updated_at     = {0}" -f $u)
}

# List the HB job and tail the HB log (if any)
$j = Get-Job -Name "pa_watchdog_heartbeat" -ErrorAction SilentlyContinue
if ($j) { Write-Host ("HB job: {0} (State={1})" -f $j.Name, $j.State) }
$hbLog = Join-Path $root 'tmp\logs\watchdog.hb.log'
if (Test-Path $hbLog) {
    Write-Host "`n-- hb log (tail 40) --"
    Get-Content $hbLog -Tail 40
}
