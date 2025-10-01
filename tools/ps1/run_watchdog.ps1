Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$RepoRoot = Get-Location
$venvPy = Join-Path $RepoRoot ".venv\Scripts\python.exe"
$py = if (Test-Path $venvPy) { $venvPy } else { "python" }

$pidDir = "tmp\pid"; if (-not (Test-Path $pidDir)) { New-Item -ItemType Directory -Force $pidDir | Out-Null }
$pidFile = Join-Path $pidDir "watchdog.pid"
if (Test-Path $pidFile) {
  try { $old = Get-Content $pidFile -ErrorAction Stop } catch { $old = "" }
  if ($old) {
    $p = Get-Process -Id ([int]$old) -ErrorAction SilentlyContinue
    if ($p) { Write-Host "Watchdog already running (PID $old)"; exit 0 }
  }
}

$logDir = "tmp\logs"; if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Force $logDir | Out-Null }
$out = Join-Path $logDir "watchdog.out.log"
$err = Join-Path $logDir "watchdog.err.log"

$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName = $py
$psi.Arguments = '-m watchdog.pa_watchdog'
$psi.WorkingDirectory = $RepoRoot
$psi.UseShellExecute = $false
$psi.CreateNoWindow = $true
$psi.RedirectStandardOutput = $true
$psi.RedirectStandardError  = $true
$p = New-Object System.Diagnostics.Process
$p.StartInfo = $psi
[void]$p.Start()

Start-Job -ScriptBlock {
  param($pid,$path)
  $proc = Get-Process -Id $pid -ErrorAction SilentlyContinue
  if (-not $proc) { return }
  $sw = [System.IO.StreamWriter]::new($path,$true,[System.Text.Encoding]::UTF8)
  try {
    while (-not $proc.HasExited) {
      $line = $proc.StandardOutput.ReadLine()
      if ($null -ne $line) { $sw.WriteLine($line) } else { Start-Sleep -Milliseconds 100 }
    }
  } catch {} finally { $sw.Flush(); $sw.Close() }
} -ArgumentList $p.Id,$out | Out-Null

Start-Job -ScriptBlock {
  param($pid,$path)
  $proc = Get-Process -Id $pid -ErrorAction SilentlyContinue
  if (-not $proc) { return }
  $sw = [System.IO.StreamWriter]::new($path,$true,[System.Text.Encoding]::UTF8)
  try {
    while (-not $proc.HasExited) {
      $line = $proc.StandardError.ReadLine()
      if ($null -ne $line) { $sw.WriteLine($line) } else { Start-Sleep -Milliseconds 100 }
    }
  } catch {} finally { $sw.Flush(); $sw.Close() }
} -ArgumentList $p.Id,$err | Out-Null

$p.Id | Set-Content -Encoding ASCII -Path $pidFile
Write-Host "Watchdog started (PID $($p.Id)). Logs: $out / $err"

# --- TUNNEL URL MONITOR (PA-361) ---
try {
  function Ensure-Dir([string]$p){ if (-not (Test-Path $p)) { New-Item -ItemType Directory -Force -Path $p | Out-Null } }
  $logDir = "tmp\logs"
  $outL = Join-Path $logDir "cloudflared.out.log"
  $errL = Join-Path $logDir "cloudflared.err.log"
  $pub  = "reports\ops\tunnel_url.txt"
  Ensure-Dir (Split-Path $pub -Parent)
  Start-Job -Name "pa_tunnel_monitor" -ScriptBlock {
    param($outL,$errL,$pub)
    $pattern = 'https?://\S*trycloudflare\.com'
    $wrote = $false
    while(-not $wrote){
      $hits = @()
      foreach($p in @($outL,$errL)){
        if (Test-Path $p) {
          $m = Select-String -Path $p -Pattern $pattern -AllMatches -ErrorAction SilentlyContinue
          if ($m) { $hits += ($m.Matches | ForEach-Object { $_.Value }) }
        }
      }
      if ($hits.Count -gt 0) {
        $first = [string]($hits | Select-Object -First 1)
        Set-Content -Encoding UTF8 -Path $pub -Value $first
        $wrote = $true
      } else {
        Start-Sleep -Milliseconds 700
      }
    }
  } -ArgumentList $outL,$errL,$pub | Out-Null
} catch {}
# --- /TUNNEL URL MONITOR ---


# --- TUNNEL URL MONITOR (PA-NONBLOCK) ---
try {
  function Ensure-Dir([string]$p){ if (-not (Test-Path $p)) { New-Item -ItemType Directory -Force -Path $p | Out-Null } }
  $logDir = "tmp\logs"
  $outL = Join-Path $logDir "cloudflared.out.log"
  $errL = Join-Path $logDir "cloudflared.err.log"
  $pub  = "reports\ops\tunnel_url.txt"
  Ensure-Dir (Split-Path $pub -Parent)
  Start-Job -Name "pa_tunnel_monitor" -ScriptBlock {
    param($outL,$errL,$pub)
    $pattern = 'https?://\S*trycloudflare\.com'
    $wrote = $false
    while(-not $wrote){
      $hits = @()
      foreach($p in @($outL,$errL)){
        if (Test-Path $p) {
          $m = Select-String -Path $p -Pattern $pattern -AllMatches -ErrorAction SilentlyContinue
          if ($m) { $hits += ($m.Matches | ForEach-Object { $_.Value }) }
        }
      }
      if ($hits.Count -gt 0) {
        $first = [string]($hits | Select-Object -First 1)
        Set-Content -Encoding UTF8 -Path $pub -Value $first
        $wrote = $true
      } else {
        Start-Sleep -Milliseconds 700
      }
    }
  } -ArgumentList $outL,$errL,$pub | Out-Null
} catch {}
# --- /TUNNEL URL MONITOR (PA-NONBLOCK) ---

