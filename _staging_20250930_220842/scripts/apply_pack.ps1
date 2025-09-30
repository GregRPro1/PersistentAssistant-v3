<# 
PA-361 TUNNEL AUTO (FIXPERMS)
- Robust cloudflared detection (PATH, Program Files, LocalAppData, tools\bin, where.exe)
- If missing, try winget -> choco -> direct download (fallback writes to %TEMP% if tools\bin is locked)
- Starts quick tunnel; parses trycloudflare URL
- Writes reports\ops\tunnel_url.txt
- Best-effort: start control server if 8776 not listening
- Commit (no push)
#>
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Ensure-Dir([string]$p){ if (-not (Test-Path $p)) { New-Item -ItemType Directory -Force -Path $p | Out-Null } }
function Is-Listening8776 {
  try { return [bool](Get-NetTCPConnection -LocalPort 8776 -ErrorAction SilentlyContinue) } catch { return $false }
}
function Find-Cloudflared {
  $cmd = Get-Command cloudflared -ErrorAction SilentlyContinue
  if ($cmd) { return $cmd.Source }
  $cands = @(
    (Join-Path (Join-Path $PSScriptRoot '..\..\tools\bin') 'cloudflared.exe'),
    (Join-Path $env:ProgramFiles 'Cloudflare\Cloudflared\cloudflared.exe'),
    (Join-Path ${env:ProgramFiles(x86)} 'Cloudflare\Cloudflared\cloudflared.exe'),
    (Join-Path $env:LOCALAPPDATA 'Cloudflare\Cloudflared\cloudflared.exe'),
    (Join-Path $env:LOCALAPPDATA 'Programs\Cloudflare\Cloudflared\cloudflared.exe'),
    (Join-Path $env:LOCALAPPDATA 'Programs\cloudflared\cloudflared.exe')
  )
  foreach ($p in $cands) { if ($p -and (Test-Path $p)) { return $p } }
  try {
    $w = & where.exe cloudflared 2>$null
    if ($LASTEXITCODE -eq 0 -and $w) { return ($w -split \"`r?`n\")[0] }
  } catch {}
  return $null
}

# Repo root is parent of scripts dir
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot  = Split-Path -Parent $ScriptDir
Push-Location $RepoRoot
Write-Host "apply_pack: repo root = $RepoRoot"

Ensure-Dir "tools\bin"
Ensure-Dir "tmp\logs"
Ensure-Dir "reports\ops"

# Ensure control server up (best-effort)
if (-not (Is-Listening8776)) {
  $server = 'tools\ps1\run_control_server_lan.ps1'
  if (Test-Path $server) {
    Write-Host "[PACK] Starting control server on 8776 (detached)"
    Start-Process pwsh -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-File', $server -WindowStyle Minimized
    Start-Sleep -Seconds 2
  }
}

# Stop prior cloudflared if any
Get-Process cloudflared -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue

# Ensure cloudflared
$cf = Find-Cloudflared
if (-not $cf) {
  Write-Host "[CF] winget install..."
  try { winget install --id Cloudflare.cloudflared -e --accept-package-agreements --accept-source-agreements -h | Out-Null } catch {}
  $cf = Find-Cloudflared
}
if (-not $cf) {
  Write-Host "[CF] choco install..."
  try { choco install cloudflared -y | Out-Null } catch {}
  $cf = Find-Cloudflared
}
if (-not $cf) {
  Write-Host "[CF] direct download..."
  $dl = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
  $toRepo = Join-Path "tools\bin" "cloudflared.exe"
  $toTmp  = Join-Path $env:TEMP "cloudflared.exe"
  try {
    # Try repo bin first
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
  # Start quick tunnel
  $ts = (Get-Date).ToString('yyyyMMdd_HHmmss')
  $log = "tmp\logs\cloudflared_$ts.log"
  $tunnelFile = "reports\ops\tunnel_url.txt"

  $psi = New-Object System.Diagnostics.ProcessStartInfo
  $psi.FileName = $cf
  $psi.Arguments = 'tunnel --no-autoupdate --url "http://127.0.0.1:8776"'
  $psi.RedirectStandardOutput = $true
  $psi.RedirectStandardError  = $true
  $psi.UseShellExecute = $false
  $psi.CreateNoWindow = $true

  $p = New-Object System.Diagnostics.Process
  $p.StartInfo = $psi
  [void]$p.Start()

  $deadline = (Get-Date).AddSeconds(25)
  $url = $null
  $sw = [System.IO.StreamWriter]::new($log,$false,[System.Text.Encoding]::UTF8)
  try {
    while (-not $p.HasExited) {
      if ((Get-Date) -gt $deadline) { break }
      while (($line = $p.StandardOutput.ReadLine()) -ne $null) {
        $sw.WriteLine($line)
        if (-not $url) {
          $m = [regex]::Match($line, 'https?://[^\s]+trycloudflare\.com')
          if ($m.Success) { $url = $m.Value }
        }
      }
      Start-Sleep -Milliseconds 80
    }
    while (($eline = $p.StandardError.ReadLine()) -ne $null) { $sw.WriteLine($eline) }
  } finally { $sw.Flush(); $sw.Close() }

  if ($url) {
    Set-Content -Encoding UTF8 -Path $tunnelFile -Value $url
    Write-Host ("Tunnel URL: " + $url)
  } else {
    Write-Warning "[CF] Tunnel URL not detected; see $log"
  }
}

# Commit
try { git add -A; git commit -m "PA-361 TUNNEL_AUTO_FIXPERMS: robust cloudflared detection/install + tunnel_url.txt" | Out-Null } catch {}

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
