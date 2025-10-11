param([int]$Port = 8787)
Set-StrictMode -Version Latest
$ErrorActionPreference = "Continue"

$exe = "cloudflared"
if (-not (Get-Command $exe -ErrorAction SilentlyContinue)) {
  $exe = "C:\Program Files (x86)\cloudflared\cloudflared.exe"
}
if (-not (Test-Path $exe)) { Write-Warning "cloudflared not found"; exit 1 }

$tunOut = ".\tmp\logs\cloudflared.out.log"; $tunErr = ".\tmp\logs\cloudflared.err.log"
$null = New-Item -ItemType Directory -Force -Path ".\tmp\logs"

$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName = $exe; $psi.Arguments = "tunnel --url http://localhost:$Port"
$psi.UseShellExecute = $false; $psi.RedirectStandardOutput = $true; $psi.RedirectStandardError = $true
$p = New-Object System.Diagnostics.Process; $p.StartInfo = $psi; $p.Start() | Out-Null

$tunnelUrl = $null; $deadline = (Get-Date).AddSeconds(30)
while ((Get-Date) -lt $deadline -and -not $tunnelUrl) {
  if ($p.HasExited) { break }
  if (-not $p.StandardOutput.EndOfStream) {
    $line = $p.StandardOutput.ReadLine(); if ($line) { Add-Content $tunOut $line }
    if ($line -match 'https?://[a-zA-Z0-9\-]+\.trycloudflare\.com') { $tunnelUrl = $Matches[0] }
  } else { Start-Sleep -Milliseconds 200 }
}

if ($tunnelUrl) {
  New-Item -ItemType Directory -Force -Path ".\reports\ops" | Out-Null
  $tunnelUrl | Set-Content ".\reports\ops\tunnel_url.txt" -Encoding UTF8
  Write-Host "Tunnel URL: $tunnelUrl"
} else { Write-Warning "No tunnel URL captured." }
