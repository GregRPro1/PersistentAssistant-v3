param([int]$Port = 8787)
Set-StrictMode -Version Latest
$ErrorActionPreference = "Continue"
. ".\pal\core\health\log.ps1"
$exe = $null
try { $exe = pwsh -NoProfile -Command ".\pal\scripts\ps\find_cloudflared.ps1" } catch {}
if (-not $exe) { try { $exe = pwsh -NoProfile -Command ".\pal\scripts\ps\find_cloudflared.ps1 -InstallIfMissing" } catch {} }
if (-not $exe -or ($exe -is [System.Array] -and $exe.Length -eq 0)) { Write-Log ".\tmp\logs\cloudflared.err.log" "error" "cloudflared not found; see find_cloudflared.ps1"; Write-Warning "cloudflared not found"; exit 1 }
if ($exe -is [System.Array]) { $exe = $exe[0] }
$tunOut = ".\tmp\logs\cloudflared.out.log"; $tunErr = ".\tmp\logs\cloudflared.err.log"; Ensure-Dir ".\tmp\logs"
Write-Log $tunOut "info" "Starting cloudflared: $exe tunnel --url http://localhost:$Port"
$psi = New-Object System.Diagnostics.ProcessStartInfo; $psi.FileName = $exe; $psi.Arguments = "tunnel --url http://localhost:$Port"; $psi.UseShellExecute = $false; $psi.RedirectStandardOutput = $true; $psi.RedirectStandardError = $true
$p = New-Object System.Diagnostics.Process; $p.StartInfo = $psi; $p.Start() | Out-Null
$tunnelUrl = $null; $deadline = (Get-Date).AddSeconds(45)
while ((Get-Date) -lt $deadline -and -not $tunnelUrl) {
  if ($p.HasExited) { break }
  if (-not $p.StandardOutput.EndOfStream) {
    $line = $p.StandardOutput.ReadLine(); if ($line) { Add-Content $tunOut $line; if ($line -match 'https?://[a-zA-Z0-9\-]+\.trycloudflare\.com') { $tunnelUrl = $Matches[0] } }
  } else { Start-Sleep -Milliseconds 200 }
}
if ($tunnelUrl) { New-Item -ItemType Directory -Force -Path ".\reports\ops" | Out-Null; $tunnelUrl | Set-Content ".\reports\ops\tunnel_url.txt" -Encoding UTF8; Write-Log $tunOut "info" "Captured tunnel URL: $tunnelUrl"; Write-Host "Tunnel URL: $tunnelUrl" } else { $err = if ($p -and -not $p.StandardError.EndOfStream) { $p.StandardError.ReadToEnd() } else { "" }; if ($err) { Add-Content $tunErr $err }; Write-Log $tunErr "warn" "No tunnel URL captured from cloudflared output."; Write-Warning "No tunnel URL captured from cloudflared output." }