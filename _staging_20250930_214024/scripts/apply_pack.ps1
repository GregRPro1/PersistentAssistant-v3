<# 
PA-361 TUNNEL AUTO (FIXARGS)
- Detect cloudflared robustly
- Install if missing (winget -> choco -> direct)
- Start quick tunnel and extract trycloudflare URL
- Write reports\ops\tunnel_url.txt
- Commit (no push)
#>
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Ensure-Dir([string]$p){ if (-not (Test-Path $p)) { New-Item -ItemType Directory -Force -Path $p | Out-Null } }
function Find-Cloudflared {
  $cmd = Get-Command cloudflared -ErrorAction SilentlyContinue
  if ($cmd) { return $cmd.Source }
  $paths = @(
    (Join-Path (Join-Path $PSScriptRoot '..\..\tools\bin') 'cloudflared.exe'),
    'C:\Program Files\Cloudflare\Cloudflared\cloudflared.exe',
    'C:\Program Files (x86)\Cloudflare\Cloudflared\cloudflared.exe'
  )
  foreach ($p in $paths) { if (Test-Path $p) { return $p } }
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

# 0) If a previous cloudflared is running, stop it to avoid conflicts
Get-Process cloudflared -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue

# 1) Ensure cloudflared
$cf = Find-Cloudflared
if (-not $cf) {
  Write-Host "[CF] Attempt winget install..."
  try {
    winget install --id Cloudflare.cloudflared -e --accept-package-agreements --accept-source-agreements -h | Out-Null
  } catch {}
  $cf = Find-Cloudflared
}
if (-not $cf) {
  Write-Host "[CF] Attempt choco install..."
  try { choco install cloudflared -y | Out-Null } catch {}
  $cf = Find-Cloudflared
}
if (-not $cf) {
  Write-Host "[CF] Attempt direct download..."
  $dl = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
  $to = Join-Path "tools\bin" "cloudflared.exe"
  try {
    Invoke-WebRequest -Uri $dl -OutFile $to -UseBasicParsing -TimeoutSec 120
    if (Test-Path $to) { $cf = $to }
  } catch {
    Write-Warning "[CF] Direct download failed: $_"
  }
}
if (-not $cf) {
  Write-Warning "[CF] cloudflared unavailable; aborting tunnel step."
  goto CommitAndSummary
}

# 2) Start quick tunnel and capture URL (use .Arguments instead of ArgumentList.AddRange)
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

:CommitAndSummary

# 3) Commit (no push)
try {
  git add -A
  git commit -m "PA-361 TUNNEL_AUTO_FIXARGS: auto-install cloudflared and write tunnel_url.txt" | Out-Null
  Write-Host "[PACK] Commit created (or nothing to commit)"
} catch {
  Write-Host "[PACK] Git commit failed (possibly no changes)"
}

# 4) Summary
Write-Host "==== PACK SUMMARY ===="
Write-Host ("Repo: " + $RepoRoot)
if (Test-Path "reports\ops\tunnel_url.txt") {
  $u = (Get-Content "reports\ops\tunnel_url.txt" -TotalCount 1)
  Write-Host ("Tunnel: " + $u)
} else {
  Write-Host "Tunnel: (no URL file)"
}
Write-Host "======================"
