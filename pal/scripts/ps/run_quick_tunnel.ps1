param(
  [int]$Port = 8787
)
Set-StrictMode -Version Latest
$ErrorActionPreference = "Continue"

$exe = "cloudflared"
$tunOut = ".\tmp\logs\cloudflared.out.log"
$tunErr = ".\tmp\logs\cloudflared.err.log"
$null = New-Item -ItemType Directory -Force -Path ".\tmp\logs"

# Start cloudflared and capture output
$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName = $exe
$psi.Arguments = "tunnel --url http://localhost:$Port"
$psi.UseShellExecute = $false
$psi.RedirectStandardOutput = $true
$psi.RedirectStandardError = $true
$p = New-Object System.Diagnostics.Process
$p.StartInfo = $psi
$p.Start() | Out-Null

# Read lines until we find the URL
$tunnelUrl = $null
for ($i=0; $i -lt 120 -and -not $tunnelUrl; $i++) {
  Start-Sleep -Milliseconds 250
  $line = $p.StandardOutput.ReadLine()
  if ($line) {
    Add-Content $tunOut $line
    if ($line -match 'https?://[a-zA-Z0-9\-]+\.trycloudflare\.com') {
      $tunnelUrl = $Matches[0]
    }
  }
  if ($p.HasExited) { break }
}

if ($tunnelUrl) {
  New-Item -ItemType Directory -Force -Path ".\reports\ops" | Out-Null
  $tunnelUrl | Set-Content ".\reports\ops\tunnel_url.txt" -Encoding UTF8
  Write-Host "Tunnel URL: $tunnelUrl"
} else {
  Write-Warning "No tunnel URL captured."
}
