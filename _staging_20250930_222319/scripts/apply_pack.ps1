<# 
PA-361 TUNNEL AUTO (HARDENED)
#>
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Ensure-Dir([string]$p){
  if (-not (Test-Path $p)) { New-Item -ItemType Directory -Force -Path $p | Out-Null }
}
function Is-Listening8776 {
  try { return [bool](Get-NetTCPConnection -LocalPort 8776 -ErrorAction SilentlyContinue) } catch { return $false }
}
function Wait-Healthz {
  param([int]$Seconds = 30)
  $deadline = (Get-Date).AddSeconds($Seconds)
  while ((Get-Date) -lt $deadline) {
    try {
      $r = Invoke-WebRequest -Uri "http://127.0.0.1:8776/healthz" -UseBasicParsing -TimeoutSec 2
      if ($r.StatusCode -eq 200) { return $true }
    } catch {}
    Start-Sleep -Seconds 1
  }
  return $false
}
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
  return $null
}

# Locate repo root
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot  = Split-Path -Parent $ScriptDir
Push-Location $RepoRoot
Write-Host "apply_pack: repo root = $RepoRoot"

Ensure-Dir "tools\bin"
Ensure-Dir "tmp\logs"
Ensure-Dir "reports\ops"

# Ensure control server is up
if (-not (Is-Listening8776)) {
  $server = 'tools\ps1\run_control_server_lan.ps1'
  if (Test-Path $server) {
    Write-Host "[PACK] Starting control server on 8776 (detached)"
    Start-Process pwsh -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-File', $server -WindowStyle Minimized | Out-Null
  }
}
if (-not (Wait-Healthz -Seconds 30)) {
  Write-Warning "[PACK] /healthz did not become ready within 30s; proceeding anyway"
}

# Stop any previous cloudflared
Get-Process cloudflared -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue

# Ensure cloudflared
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
if (-not $cf) {
  Write-Warning "[CF] cloudflared unavailable; tunnel step skipped."
} else {
  Write-Host "[CF] using: $cf"
  $ts = Get-Date -Format "yyyyMMdd_HHmmss"
  $log = Join-Path $RepoRoot ("tmp\logs\cloudflared_{0}.log" -f $ts)
  $err = Join-Path $RepoRoot ("tmp\logs\cloudflared_{0}.err.log" -f $ts)
  $tunnelFile = Join-Path $RepoRoot 'reports\ops\tunnel_url.txt'

  # .NET Process for live capture
  $psi = New-Object System.Diagnostics.ProcessStartInfo
  $psi.FileName = $cf
  $psi.Arguments = 'tunnel --no-autoupdate --loglevel info --url "http://127.0.0.1:8776"'
  $psi.RedirectStandardOutput = $true
  $psi.RedirectStandardError  = $true
  $psi.UseShellExecute = $false
  $psi.CreateNoWindow = $true

  $p = New-Object System.Diagnostics.Process
  $p.StartInfo = $psi
  [void]$p.Start()

  $swOut = [System.IO.StreamWriter]::new($log,$false,[System.Text.Encoding]::UTF8)
  $swErr = [System.IO.StreamWriter]::new($err,$false,[System.Text.Encoding]::UTF8)

  $deadline = (Get-Date).AddSeconds(120)
  $url = $null
  try {
    while ((Get-Date) -lt $deadline) {
      while (($line = $p.StandardOutput.ReadLine()) -ne $null) {
        $swOut.WriteLine($line)
        if (-not $url) {
          $m = [regex]::Match($line, 'https?://\S*trycloudflare\.com')
          if ($m.Success) { $url = $m.Value; break }
        }
      }
      if ($url) { break }
      while (($eline = $p.StandardError.ReadLine()) -ne $null) {
        $swErr.WriteLine($eline)
        if (-not $url) {
          $m2 = [regex]::Match($eline, 'https?://\S*trycloudflare\.com')
          if ($m2.Success) { $url = $m2.Value; break }
        }
      }
      if ($url) { break }
      Start-Sleep -Milliseconds 200
    }
  } finally { $swOut.Flush(); $swOut.Close(); $swErr.Flush(); $swErr.Close() }

  if ($url) {
    Set-Content -Encoding UTF8 -Path $tunnelFile -Value $url
    Write-Host ("Tunnel URL: " + $url)
  } else {
    Write-Warning "[CF] Tunnel URL not detected in allotted time; check logs:"
    Write-Host ("   OUT: " + $log)
    Write-Host ("   ERR: " + $err)
  }
}

# Commit (no push)
try { git add -A; git commit -m "PA-361 TUNNEL_AUTO_HARDENED: robust detection + live capture + tunnel_url.txt" | Out-Null } catch {}

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
