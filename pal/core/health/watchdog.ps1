param([string]$ConfigPath = ".\pal\config\pal_watchdog.json")

function Read-Config {
  param([string]$Path)
  if (-not (Test-Path $Path)) { throw "Config not found: $Path" }
  (Get-Content -Raw $Path) | ConvertFrom-Json
}

function Job-Running {
  param([string]$Name)
  $j = Get-Job -Name $Name -ErrorAction SilentlyContinue
  if (-not $j) { return $false }
  return ($j.State -eq 'Running')
}

function Start-Server {
  param($cfg, [string]$Root)
  if (-not $cfg.enable_server) { return }
  if (-not (Job-Running -Name "pal-server")) {
    Write-Host "[WD] starting pal-server…" -ForegroundColor Yellow
    Start-Job -Name "pal-server" -ScriptBlock {
      Set-Location $using:Root
      pwsh -File ".\current\run.ps1"
    } | Out-Null
  }
}

function Start-Tracker {
  param($cfg, [string]$Root)
  if (-not $cfg.enable_tracker) { return }
  if (-not (Job-Running -Name "pal-tracker")) {
    $python = "$env:VIRTUAL_ENV\Scripts\python.exe"
    if (-not (Test-Path $python)) { $python = "python" }
    Write-Host "[WD] starting pal-tracker…" -ForegroundColor Yellow
    Start-Job -Name "pal-tracker" -ScriptBlock {
      param($py, $plan, $root)
      Set-Location $root
      & $py ".\pal\ui\desktop\pal_tracker.py" $plan
    } -ArgumentList $python, $cfg.plan_path, $Root | Out-Null
  }
}

function Check-Health {
  param($cfg)
  $url = "http://{0}:{1}/healthz" -f $cfg.server.host, $cfg.server.port
  try {
    $r = Invoke-WebRequest -Uri $url -TimeoutSec 5
    return ($r.StatusCode -eq 200)
  } catch {
    return $false
  }
}

function Rollback-And-Restart {
  param([string]$Root)
  Write-Warning "[WD] health failed → rollback to last _good"
  $good = Get-ChildItem (Join-Path $Root "releases") -Directory |
          Where-Object { Test-Path (Join-Path $_.FullName "_good") } |
          Sort-Object Name -Descending | Select-Object -First 1
  if ($good) {
    if (Test-Path (Join-Path $Root "current")) { cmd /c rmdir current | Out-Null }
    cmd /c mklink /J current "$($good.FullName)" | Out-Null
    $srv = Get-Job -Name "pal-server" -ErrorAction SilentlyContinue
    if ($srv) { Stop-Job $srv -Force -ErrorAction SilentlyContinue | Out-Null }
    Start-Server -cfg $global:cfg -Root $Root
  } else {
    Write-Error "[WD] no _good release found"
  }
}

# MAIN
$Root = (Get-Location).Path
$global:cfg = Read-Config -Path $ConfigPath
$interval = [int]$global:cfg.interval_secs; if ($interval -lt 5) { $interval = 15 }

Write-Host "[WD] PAL Watchdog starting with $ConfigPath"

while ($true) {
  try {
    $global:cfg = Read-Config -Path $ConfigPath

    Start-Server  -cfg $global:cfg -Root $Root
    Start-Tracker -cfg $global:cfg -Root $Root

    if ($global:cfg.enable_server) {
      $ok = Check-Health -cfg $global:cfg
      if (-not $ok) { Rollback-And-Restart -Root $Root }
    }

    if ($global:cfg.enable_ping) {
      try {
        $client = New-Object System.Net.Sockets.TcpClient
        $iar = $client.BeginConnect($global:cfg.ping.host, [int]$global:cfg.ping.port, $null, $null)
        $pingok = $iar.AsyncWaitHandle.WaitOne(3000)
        $client.Close()
        Write-Host ("[WD] ping {0}:{1} {2}" -f $global:cfg.ping.host, $global:cfg.ping.port, ($(if($pingok){"OK"}else{"FAIL"})))
      } catch { Write-Host "[WD] ping ERR $($_.Exception.Message)" }
    }
  } catch {
    Write-Warning "[WD] loop error: $($_.Exception.Message)"
  }
  Start-Sleep -Seconds $interval
}
