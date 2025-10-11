param([string]$ConfigPath = ".\pal\config\pal_watchdog.json")

# ---------- utils ----------
function Read-Config {
  param([string]$Path)
  if (-not (Test-Path $Path)) { throw "Config not found: $Path" }
  (Get-Content -Raw $Path) | ConvertFrom-Json
}
function Job-Running { param([string]$Name)
  $j = Get-Job -Name $Name -ErrorAction SilentlyContinue
  if (-not $j) { return $false }
  return ($j.State -eq 'Running')
}
function Stop-JobSafe { param([string]$Name, [int]$TimeoutSec = 10)
  $j = Get-Job -Name $Name -ErrorAction SilentlyContinue
  if (-not $j) { return }
  try { Stop-Job -Job $j -Force -ErrorAction SilentlyContinue } catch {}
  $sw = [Diagnostics.Stopwatch]::StartNew()
  while ($sw.Elapsed.TotalSeconds -lt $TimeoutSec) {
    $j = Get-Job -Name $Name -ErrorAction SilentlyContinue
    if (-not $j -or $j.State -in 'Stopped','Completed','Failed') { break }
    Start-Sleep 0.2
  }
  try { Remove-Job -Name $Name -Force -ErrorAction SilentlyContinue } catch {}
}

# ---------- components ----------
function Start-Server { param($cfg, [string]$Root)
  if (-not $cfg.enable_server) { return }
  if (-not (Job-Running -Name "pal-server")) {
    Write-Host "[WD] starting pal-server…" -ForegroundColor Yellow
    Start-Job -Name "pal-server" -ScriptBlock {
      Set-Location $using:Root
      pwsh -File ".\current\run.ps1"
    } | Out-Null
  }
}
function Start-Tracker { param($cfg, [string]$Root)
  if (-not $cfg.enable_tracker) { return }
  if (-not (Job-Running -Name "pal-tracker")) {
    $python = "$env:VIRTUAL_ENV\Scripts\python.exe"
    if (-not (Test-Path $python)) { $python = "python" }
    Write-Host "[WD] starting pal-tracker…" -ForegroundColor Yellow
    Start-Job -Name "pal-tracker" -ScriptBlock {
      param($py,$plan,$root)
      Set-Location $root
      & $py ".\pal\ui\desktop\pal_tracker.py" $plan
    } -ArgumentList $python, $cfg.plan_path, $Root | Out-Null
  }
}
function Check-Health { param($cfg)
  $url = "http://{0}:{1}/healthz" -f $cfg.server.host, $cfg.server.port
  try { (Invoke-WebRequest -Uri $url -TimeoutSec 5).StatusCode -eq 200 } catch { $false }
}
function Rollback-And-Restart { param([string]$Root, $cfg)
  Write-Warning "[WD] health failed → rollback to last _good"
  $good = Get-ChildItem (Join-Path $Root "releases") -Directory |
          Where-Object { Test-Path (Join-Path $_.FullName "_good") } |
          Sort-Object Name -Descending | Select-Object -First 1
  if ($good) {
    if (Test-Path (Join-Path $Root "current")) { cmd /c rmdir current | Out-Null }
    cmd /c mklink /J current "$($good.FullName)" | Out-Null
    Stop-JobSafe -Name "pal-server"
    Start-Server -cfg $cfg -Root $Root
  } else {
    Write-Error "[WD] no _good release found"
  }
}

# ---------- request queue ----------
$ReqDir = ".\pal\control\requests"
$AckDir = ".\pal\control\acks"
$DoneDir = ".\pal\control\processed"
mkdir -Force $ReqDir,$AckDir,$DoneDir | Out-Null

function Ack-Request { param([string]$ReqPath, [hashtable]$Result)
  $name = [IO.Path]::GetFileNameWithoutExtension($ReqPath)
  $ackPath = Join-Path $AckDir "$name.ack.json"
  ($Result | ConvertTo-Json -Depth 8) | Set-Content $ackPath -Encoding UTF8
  Move-Item -LiteralPath $ReqPath -Destination (Join-Path $DoneDir ([IO.Path]::GetFileName($ReqPath))) -Force
}

function Process-Request-File { param([string]$ReqPath, $cfg, [string]$Root)
  try {
    $req = Get-Content -Raw $ReqPath | ConvertFrom-Json
  } catch {
    Ack-Request -ReqPath $ReqPath -Result @{ ok=$false; error="invalid json: $($_.Exception.Message)"; file=$ReqPath }
    return
  }
  $cmd = ($req.command + "").ToLower()
  $target = ($req.target + "").ToLower()
  $ok = $true; $msg = ""

  switch ($cmd) {
    'start'   { if ($target -eq 'server') { Start-Server -cfg $cfg -Root $Root }
                elseif ($target -eq 'tracker') { Start-Tracker -cfg $cfg -Root $Root }
                else { $ok=$false; $msg="unknown target '$target'" } }
    'stop'    { if ($target -eq 'server') { Stop-JobSafe -Name 'pal-server' }
                elseif ($target -eq 'tracker') { Stop-JobSafe -Name 'pal-tracker' }
                else { $ok=$false; $msg="unknown target '$target'" } }
    'restart' { if ($target -eq 'server') { Stop-JobSafe -Name 'pal-server'; Start-Server -cfg $cfg -Root $Root }
                elseif ($target -eq 'tracker') { Stop-JobSafe -Name 'pal-tracker'; Start-Tracker -cfg $cfg -Root $Root }
                else { $ok=$false; $msg="unknown target '$target'" } }
    'health_check' { $ok = Check-Health -cfg $cfg; $msg = "health="+($ok) }
    'reload_config' { $script:cfg = Read-Config -Path $ConfigPath; $msg="reloaded" }
    'shutdown' { Stop-JobSafe -Name 'pal-tracker'; Stop-JobSafe -Name 'pal-server'; $msg="stopped all" }
    default { $ok = $false; $msg = "unknown command '$cmd'" }
  }

  Ack-Request -ReqPath $ReqPath -Result @{
    ok = $ok; message = $msg; command = $cmd; target = $target; ts = (Get-Date).ToString("s")
  }
}

# ---------- main loop ----------
$Root = (Get-Location).Path
$script:cfg = Read-Config -Path $ConfigPath
$interval = [int]$cfg.interval_secs; if ($interval -lt 5) { $interval = 15 }

Write-Host "[WD] starting with $ConfigPath (interval=${interval}s)"

while ($true) {
  try {
    # re-read live config each pass
    $script:cfg = Read-Config -Path $ConfigPath

    # ensure components running
    Start-Server  -cfg $cfg -Root $Root
    Start-Tracker -cfg $cfg -Root $Root

    # health + rollback
    if ($cfg.enable_server) {
      if (-not (Check-Health -cfg $cfg)) { Rollback-And-Restart -Root $Root -cfg $cfg }
    }

    # process request files (oldest first)
    Get-ChildItem $ReqDir -Filter *.json -File | Sort-Object LastWriteTime |
      ForEach-Object { Process-Request-File -ReqPath $_.FullName -cfg $cfg -Root $Root }

  } catch {
    Write-Warning "[WD] loop error: $($_.Exception.Message)"
  }
  Start-Sleep -Seconds $interval
}
