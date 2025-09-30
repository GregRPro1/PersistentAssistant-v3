param(
  [string]$Bind = "http://127.0.0.1:8776",
  [string]$LogDir = (Join-Path $PSScriptRoot '..\..\tmp\logs')
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Ensure-Dir([string]$p){ if (-not (Test-Path $p)) { New-Item -ItemType Directory -Force -Path $p | Out-Null } }
Ensure-Dir $LogDir
Ensure-Dir (Join-Path $PSScriptRoot '..\..\reports\ops')

# Verify cloudflared
$exe = (Get-Command cloudflared -ErrorAction SilentlyContinue)
if (-not $exe) {
  $bin = Join-Path (Join-Path $PSScriptRoot '..\bin') 'cloudflared.exe'
  if (Test-Path $bin) { $exe = @{ Source = $bin } }
}
if (-not $exe) { Write-Warning "[CF] cloudflared not available; skipping tunnel."; exit 0 }

$ts = (Get-Date).ToString('yyyyMMdd_HHmmss')
$logFile = Join-Path $LogDir ("cloudflared_" + $ts + ".log")
$tunnelFile = Join-Path (Join-Path $PSScriptRoot '..\..\reports\ops') 'tunnel_url.txt'

# Start cloudflared as a background process with redirected output
$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName = $exe.Source
$psi.ArgumentList.AddRange(@('tunnel','--no-autoupdate','--url', $Bind))
$psi.RedirectStandardOutput = $true
$psi.RedirectStandardError  = $true
$psi.UseShellExecute = $false
$psi.CreateNoWindow = $true

$p = New-Object System.Diagnostics.Process
$p.StartInfo = $psi
[void]$p.Start()

# Read lines asynchronously for up to 25 seconds to capture the public URL
$deadline = (Get-Date).AddSeconds(25)
$url = $null
$sw = New-Object System.IO.StreamWriter($logFile, $false, [System.Text.Encoding]::UTF8)
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
  # Also drain stderr
  while (($eline = $p.StandardError.ReadLine()) -ne $null) { $sw.WriteLine($eline) }
} finally {
  $sw.Flush(); $sw.Close()
}

if ($url) {
  Set-Content -Encoding UTF8 -Path $tunnelFile -Value $url
  Write-Host ("Tunnel URL: " + $url)
} else {
  Write-Warning "[CF] Tunnel URL not detected in time. Check log: $logFile"
}
exit 0
