# tools\ps1\run_watchdog.ps1
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# --- Paths / env ---
$RepoRoot = Get-Location
$venvPy = Join-Path $RepoRoot ".venv\Scripts\python.exe"
$py = if (Test-Path $venvPy) { $venvPy } else { "python" }

# PID file used by stop_watchdog.ps1
$pidDir = "tmp\pid"; if (-not (Test-Path $pidDir)) { New-Item -ItemType Directory -Force $pidDir | Out-Null }
$pidFile = Join-Path $pidDir "watchdog.pid"

# If PID points to a running process, bail out early
if (Test-Path $pidFile) {
  try { $old = (Get-Content $pidFile -ErrorAction Stop).Trim() } catch { $old = "" }
  if ($old) {
    $p = Get-Process -Id ([int]$old) -ErrorAction SilentlyContinue
    if ($p) { Write-Host "Watchdog already running (PID $old)"; exit 0 }
  }
}

# Logs
$logDir = "tmp\logs"; if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Force $logDir | Out-Null }
$out = Join-Path $logDir "watchdog.out.log"
$err = Join-Path $logDir "watchdog.err.log"
# Ensure logs exist even if the process never writes
New-Item -ItemType File -Force -Path $out | Out-Null
New-Item -ItemType File -Force -Path $err | Out-Null

# --- Start Python watchdog process ---
$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName = $py
$psi.Arguments = '-m watchdog.pa_watchdog'
$psi.WorkingDirectory = $RepoRoot
$psi.UseShellExecute = $false
$psi.CreateNoWindow = $true
$psi.RedirectStandardOutput = $true
$psi.RedirectStandardError = $true
$p = New-Object System.Diagnostics.Process
$p.StartInfo = $psi
[void]$p.Start()

# Save the child's PID (stop_watchdog.ps1 uses this)
$p.Id | Set-Content -Encoding ASCII -Path $pidFile

# --- Stream fan-out: stdout -> file (non-blocking) ---
Start-Job -Name "pa_watchdog_stdout" -ScriptBlock {
  param($pid, $path)
  try {
    $proc = Get-Process -Id $pid -ErrorAction SilentlyContinue
    if (-not $proc) { return }
    $sw = [System.IO.StreamWriter]::new($path, $true, [System.Text.Encoding]::UTF8)
    try {
      while (-not $proc.HasExited) {
        $line = $proc.StandardOutput.ReadLine()
        if ($null -ne $line) { $sw.WriteLine($line) } else { Start-Sleep -Milliseconds 100 }
      }
    }
    catch {} finally { $sw.Flush(); $sw.Close() }
  }
  catch {}
} -ArgumentList $p.Id, $out | Out-Null

# --- Stream fan-out: stderr -> file (non-blocking) ---
Start-Job -Name "pa_watchdog_stderr" -ScriptBlock {
  param($pid, $path)
  try {
    $proc = Get-Process -Id $pid -ErrorAction SilentlyContinue
    if (-not $proc) { return }
    $sw = [System.IO.StreamWriter]::new($path, $true, [System.Text.Encoding]::UTF8)
    try {
      while (-not $proc.HasExited) {
        $line = $proc.StandardError.ReadLine()
        if ($null -ne $line) { $sw.WriteLine($line) } else { Start-Sleep -Milliseconds 100 }
      }
    }
    catch {} finally { $sw.Flush(); $sw.Close() }
  }
  catch {}
} -ArgumentList $p.Id, $err | Out-Null

# --- Single TUNNEL URL MONITOR (deduped) ---
try {
  # kill any stale copy with the same name to avoid conflicts
  $j = Get-Job -Name "pa_tunnel_monitor" -ErrorAction SilentlyContinue
  if ($j) { Stop-Job $j -Force -ErrorAction SilentlyContinue; Remove-Job $j -Force -ErrorAction SilentlyContinue }

  function Ensure-Dir([string]$p) { if (-not (Test-Path $p)) { New-Item -ItemType Directory -Force -Path $p | Out-Null } }
  $outL = Join-Path $logDir "cloudflared.out.log"
  $errL = Join-Path $logDir "cloudflared.err.log"
  $pub = "reports\ops\tunnel_url.txt"
  Ensure-Dir (Split-Path $pub -Parent)

  Start-Job -Name "pa_tunnel_monitor" -ScriptBlock {
    param($outL, $errL, $pub)
    $pattern = 'https?://\S*trycloudflare\.com'
    $last = $null
    while ($true) {
      $hits = @()
      foreach ($p in @($outL, $errL)) {
        if (Test-Path $p) {
          try {
            $m = Select-String -Path $p -Pattern $pattern -AllMatches -ErrorAction SilentlyContinue
            if ($m) { $hits += ($m.Matches | ForEach-Object { $_.Value }) }
          }
          catch {}
        }
      }
      if ($hits.Count -gt 0) {
        $new = [string]($hits | Select-Object -Last 1)
        if ($new -and $new -ne $last) {
          Set-Content -Encoding UTF8 -Path $pub -Value $new
          $last = $new
        }
      }
      Start-Sleep -Milliseconds 700
    }
  } -ArgumentList $outL, $errL, $pub | Out-Null
}
catch {}

# --- NEW: Heartbeat writer (hardened: atomic write + log) ---
try {
  $hbJob = Get-Job -Name "pa_watchdog_heartbeat" -ErrorAction SilentlyContinue
  if ($hbJob) { Stop-Job $hbJob -Force -ErrorAction SilentlyContinue; Remove-Job $hbJob -Force -ErrorAction SilentlyContinue }

  Start-Job -Name "pa_watchdog_heartbeat" -ScriptBlock {
    param($repoRoot, $childPid)
    $base = 'http://127.0.0.1:8776'
    $opsDir = Join-Path $repoRoot 'reports\ops'
    $logDir = Join-Path $repoRoot 'tmp\logs'
    $status = Join-Path $opsDir  'watchdog_status.json'
    $hbLog = Join-Path $logDir  'watchdog.hb.log'

    # ensure dirs + hb log
    foreach ($d in @($opsDir, $logDir)) { if (-not (Test-Path $d)) { New-Item -ItemType Directory -Force $d | Out-Null } }
    if (-not (Test-Path $hbLog)) { New-Item -ItemType File -Path $hbLog -Force | Out-Null }

    function Write-Line($msg) {
      $ts = (Get-Date).ToString('s')
      Add-Content -LiteralPath $hbLog -Encoding UTF8 -Value ("[$ts] {0}" -f $msg)
    }

    function Try-Healthz($base) {
      $o = @{ ok = $false; code = 0; err = $null }
      try {
        $r = Invoke-WebRequest -Uri "$base/healthz" -UseBasicParsing -TimeoutSec 2
        $o.ok = ($r.StatusCode -eq 200); $o.code = $r.StatusCode
      }
      catch { $o.err = $_.Exception.Message }
      return $o
    }

    function Is-PortListening([int]$port) {
      try { return [bool](Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue) }
      catch { return $false }
    }

    function LatestTunnelUrl($opsDir, $logDir) {
      $txt = Join-Path $opsDir 'tunnel_url.txt'
      if (Test-Path $txt) {
        try {
          $raw = Get-Content -LiteralPath $txt -Raw
          $m = [regex]::Match($raw, 'https?://\S*trycloudflare\.com'); if ($m.Success) { return $m.Value.Trim() }
        }
        catch {}
      }
      foreach ($p in @('cloudflared.out.log', 'cloudflared.err.log')) {
        $full = Join-Path $logDir $p
        if (Test-Path $full) {
          try {
            $last = Select-String -Path $full -Pattern 'https?://\S*trycloudflare\.com' -AllMatches -ErrorAction SilentlyContinue |
            ForEach-Object { $_.Matches.Value } | Select-Object -Last 1
            if ($last) { return $last.Trim() }
          }
          catch {}
        }
      }
      return $null
    }

    function Write-JsonAtomic([string]$path, [string]$json) {
      $dir = Split-Path $path -Parent
      if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }
      $tmp = "$path.tmp"
      try {
        # allow readers while we write
        $fs = [System.IO.FileStream]::new($tmp, [System.IO.FileMode]::Create, [System.IO.FileAccess]::Write, [System.IO.FileShare]::Read)
        $sw = New-Object System.IO.StreamWriter($fs, [System.Text.Encoding]::UTF8)
        $sw.Write($json); $sw.Flush(); $sw.Dispose(); $fs.Dispose()
        Move-Item -LiteralPath $tmp -Destination $path -Force
        return $true
      }
      catch {
        if (Test-Path $tmp) { Remove-Item $tmp -Force -ErrorAction SilentlyContinue }
        Write-Line ("HB write failed: {0}" -f $_.Exception.Message)
        return $false
      }
    }

    Write-Line "Heartbeat job started (pid=$childPid)"

    while ($true) {
      try {
        $now = Get-Date
        $health = Try-Healthz $base
        $portUp = Is-PortListening 8776
        $tunnel = LatestTunnelUrl $opsDir $logDir

        $doc = [ordered]@{
          ok         = $health.ok -and $portUp
          updated_at = $now.ToString('s')
          processes  = [ordered]@{
            watchdog = @{ pid = $childPid; state = 'running' }
            server   = @{ port_8776 = $portUp; healthz = $health }
            tunnel   = @{ url = $tunnel; state = ($tunnel ? 'healthy' : 'unknown') }
          }
        }

        $json = $doc | ConvertTo-Json -Depth 10
        if (Write-JsonAtomic $status $json) {
          Write-Line ("HB ok -> {0}" -f $status)
        }
      }
      catch {
        Write-Line ("HB loop error: {0}" -f $_.Exception.Message)
      }
      Start-Sleep -Seconds 5
    }
  } -ArgumentList $RepoRoot, $p.Id | Out-Null
}
catch {}


Write-Host "Watchdog started (PID $($p.Id)). Logs: $out / $err"
