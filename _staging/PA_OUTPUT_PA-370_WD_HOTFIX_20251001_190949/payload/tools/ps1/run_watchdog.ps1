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

$scriptPath = Join-Path $RepoRoot "watchdog\pa_watchdog.py"

$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName = $py
$psi.Arguments = ('-u "{0}"' -f $scriptPath)
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
