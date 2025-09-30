<# 
PA-361 TUNNEL AUTO (MIN)
- Conservative PowerShell (no exotic syntax)
- Detect cloudflared (PATH, tools\bin, Program Files, LocalAppData, where.exe)
- Install if missing (winget -> choco -> direct to tools\bin or %TEMP%)
- Start quick tunnel and parse trycloudflare URL from log
- Write reports\ops\tunnel_url.txt
- Start control server first if 8776 isn’t listening
- Commit (no push)
#>
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Ensure-Dir([string]$p){
  if (-not (Test-Path $p)) { New-Item -ItemType Directory -Force -Path $p | Out-Null }
}

function Is-Listening8776 {
  try { return [bool](Get-NetTCPConnection -LocalPort 8776 -ErrorAction SilentlyContinue) } catch { return $false }
}

# Determine repo root (parent of this script folder)
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot  = Split-Path -Parent $ScriptDir
Push-Location $RepoRoot
Write-Host "apply_pack: repo root = $RepoRoot"

Ensure-Dir "tools\bin"
Ensure-Dir "tmp\logs"
Ensure-Dir "reports\ops"

function Find-Cloudflared {
  param([string]$RepoRoot)
  $cmd = Get-Command cloudflared -ErrorAction SilentlyContinue
  if ($cmd) { return $cmd.Source }

  $cands = @()
  $cands += (Join-Path $RepoRoot 'tools\bin\cloudflared.exe')
  if ($env:ProgramFiles) { $cands += (Join-Path $env:ProgramFiles 'Cloudflare\Cloudflared\cloudflared.exe') }
  if ($env:LOCALAPPDATA) {
    $cands += (Join-Path $env:LOCALAPPDATA 'Cloudflare\Cloudflared\cloudflared.exe')
    $cands += (Join-Path $env:LOCALAPPDATA 'Programs\Cloudflare\Cloudflared\cloudflared.exe')
    $cands += (Join-Path $env:LOCALAPPDATA 'Programs\cloudflared\cloudflared.exe')
  }
  foreach ($p in $cands) { if ($p -and (Test-Path $p)) { return $p } }

  try {
    $w = & where.exe cloudflared 2>$null
    if ($LASTEXITCODE -eq 0 -and $w) {
      $lines = $w -split "`r`n"
      if ($lines.Length -gt 0) { return $lines[0] }
    }
  } catch {}

  return $null
}

# Ensure control server is up
if (-not (Is-Listening8776)) {
  $server = 'tools\ps1\run_control_server_lan.ps1'
  if (Test-Path $server) {
    Write-Host "[PACK] Starting control server on 8776 (detached)"
    Start-Process pwsh -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-File', $server -WindowStyle Minimized | Out-Null
    Start-Sleep -Seconds 2
  }
}

# Stop any previous cloudflared
Get-Process cloudflared -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue

# Ensure cloudflared exists
$cf = Find-Cloudflared -RepoRoot $RepoRoot
if (-not $cf) {
  Write-Host "[CF] winget install..."
  try { winget install --id Cloudflare.cloudflared -e --accept-package-agreements --accept-source-agreements -h | Out-Null } catch {}
  $cf = Find-Cloudflared -RepoRoot $RepoRoot
}
if (-not $cf) {
  Write-Host "[CF] choco install..."
  try { choco install cloudflared -y | Out-Null } catch {}
  $cf = Find-Cloudflared -RepoRoot $RepoRoot
}
if (-not $cf) {
  Write-Host "[CF] direct download..."
  $dl = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
  $toRepo = Join-Path $RepoRoot 'tools\bin\cloudflared.exe'
  $toTmp  = Join-Path $env:TEMP 'cloudflared.exe'
  try {
    Invoke-WebRequest -Uri $dl -OutFile $toRepo -UseBasicParsing -TimeoutSec 120
    if (Test-Path $toRepo) { $cf = $toRepo }
  } catch {
    Write-Warning "[CF] write to tools\bin denied, falling back to %TEMP%"
    try {
      Invoke-WebRequest -Uri $dl -OutFile $toTmp -UseBasicParsing -TimeoutSec 120
      if (Test-Path $toTmp) { $cf = $toTmp }
    } catch {
      Write-Warning "[CF] Direct download failed: $_"
    }
  }
}

if ($cf) {
  Write-Host "[CF] using: $cf"
  $ts = Get-Date -Format "yyyyMMdd_HHmmss"
  $log = Join-Path $RepoRoot ("tmp\logs\cloudflared_{0}.log" -f $ts)
  $err = Join-Path $RepoRoot ("tmp\logs\cloudflared_{0}.err.log" -f $ts)
  $tunnelFile = Join-Path $RepoRoot 'reports\ops\tunnel_url.txt'

  # Start quick tunnel and redirect output to log files
  $args = @('tunnel','--no-autoupdate','--url','http://127.0.0.1:8776')
  Start-Process -FilePath $cf -ArgumentList $args -RedirectStandardOutput $log -RedirectStandardError $err -NoNewWindow -PassThru | Out-Null

  # Poll the log for the URL
  $url = $null
  for ($i=0; $i -lt 30; $i++) {
    if (Test-Path $log) {
      $txt = Get-Content $log -Raw -ErrorAction SilentlyContinue
      if ($txt) {
        $m = [regex]::Match($txt, 'https?://\S*trycloudflare\.com')
        if ($m.Success) { $url = $m.Value; break }
      }
    }
    Start-Sleep -Seconds 1
  }

  if ($url) {
    Set-Content -Encoding UTF8 -Path $tunnelFile -Value $url
    Write-Host ("Tunnel URL: " + $url)
  } else {
    Write-Warning "[CF] Tunnel URL not detected yet; check logs:"
    Write-Host ("   OUT: " + $log)
    Write-Host ("   ERR: " + $err)
  }
} else {
  Write-Warning "[CF] cloudflared unavailable; tunnel step skipped."
}

# Commit (no push)
try { git add -A; git commit -m "PA-361 TUNNEL_AUTO_MIN: conservative tunnel bring-up + tunnel_url.txt" | Out-Null } catch {}

# Summary
Write-Host "==== PACK SUMMARY ===="
Write-Host ("Repo: " + $RepoRoot)
if (Test-Path "reports\ops\tunnel_url.txt") {
  $u = (Get-Content "reports\ops\tunnel_url.txt" -TotalCount 1)
  Write-Host ("Tunnel: " + $u)
} else {
  Write-Host "Tunnel: (no URL file)"
}
Write-Host "======================"
