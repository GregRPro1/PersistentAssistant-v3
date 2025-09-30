<# 
PA-361 TUNNEL AUTO — installs cloudflared if missing (winget -> choco -> direct), then runs quick tunnel and writes reports\ops\tunnel_url.txt.
#>
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Ensure-Dir([string]$p){ if (-not (Test-Path $p)) { New-Item -ItemType Directory -Force -Path $p | Out-Null } }

# Repo root is parent of scripts dir
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot  = Split-Path -Parent $ScriptDir
Push-Location $RepoRoot
Write-Host "apply_pack: repo root = $RepoRoot"

Ensure-Dir "tools\bin"
Ensure-Dir "tmp\logs"
Ensure-Dir "reports\ops"

# 1) Install cloudflared if missing (tries winget, then choco, then direct download)
function Test-Cloudflared {
  $cmd = Get-Command cloudflared -ErrorAction SilentlyContinue
  if ($cmd) { return $true }
  $local = Join-Path "tools\bin" "cloudflared.exe"
  if (Test-Path $local) {
    $env:PATH = (Join-Path (Get-Location) "tools\bin") + [System.IO.Path]::PathSeparator + $env:PATH
    return $true
  }
  return $false
}

if (-not (Test-Cloudflared)) {
  Write-Host "[CF] Attempt winget install..."
  try {
    winget install --id Cloudflare.cloudflared -e --accept-package-agreements --accept-source-agreements -h
  } catch {}
}

if (-not (Test-Cloudflared)) {
  Write-Host "[CF] Attempt choco install..."
  try { choco install cloudflared -y } catch {}
}

if (-not (Test-Cloudflared)) {
  Write-Host "[CF] Attempt direct download..."
  $dl = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
  $to = Join-Path "tools\bin" "cloudflared.exe"
  try {
    Invoke-WebRequest -Uri $dl -OutFile $to -UseBasicParsing -TimeoutSec 120
    if (Test-Path $to) {
      $env:PATH = (Join-Path (Get-Location) "tools\bin") + [System.IO.Path]::PathSeparator + $env:PATH
      Write-Host "[CF] Downloaded cloudflared to $to"
    }
  } catch {
    Write-Warning "[CF] Direct download failed: $_"
  }
}

if (-not (Test-Cloudflared)) {
  Write-Warning "[CF] cloudflared still not available; aborting tunnel step."
  exit 0
}

# 2) Run quick tunnel and capture URL
$ts = (Get-Date).ToString('yyyyMMdd_HHmmss')
$log = "tmp\logs\cloudflared_$ts.log"
$tunnelFile = "reports\ops\tunnel_url.txt"

# Start quick tunnel and parse URL
$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName = "cloudflared"
$psi.ArgumentList.AddRange(@('tunnel','--no-autoupdate','--url','http://127.0.0.1:8776'))
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
    Start-Sleep -Milliseconds 100
  }
  while (($eline = $p.StandardError.ReadLine()) -ne $null) { $sw.WriteLine($eline) }
} finally { $sw.Flush(); $sw.Close() }

if ($url) {
  Set-Content -Encoding UTF8 -Path $tunnelFile -Value $url
  Write-Host ("Tunnel URL: " + $url)
} else {
  Write-Warning "[CF] Tunnel URL not detected; see $log"
}

# 3) API echo (best-effort)
try {
  $api = Invoke-RestMethod -Uri http://127.0.0.1:8776/api/tunnel -Method Get -TimeoutSec 3
  $apiOut = $api | ConvertTo-Json -Depth 4
  Write-Host "[PACK] /api/tunnel:"
  Write-Host $apiOut
} catch {}

# 4) Commit (no push)
try {
  git add -A
  git commit -m "PA-361 TUNNEL_AUTO: ensure cloudflared available and write tunnel_url.txt" | Out-Null
  Write-Host "[PACK] Commit created (or nothing to commit)"
} catch {
  Write-Host "[PACK] Git commit failed (possibly no changes)"
}

Write-Host "==== PACK SUMMARY ===="
Write-Host ("Repo: " + $RepoRoot)
if (Test-Path $tunnelFile) {
  $u = (Get-Content $tunnelFile -TotalCount 1)
  Write-Host ("Tunnel: " + $u)
} else {
  Write-Host "Tunnel: (no URL file)"
}
Write-Host "======================"
