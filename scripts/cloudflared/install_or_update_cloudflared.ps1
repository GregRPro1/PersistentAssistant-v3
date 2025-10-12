# Installs or updates cloudflared on Windows (x64)
Param([switch]$Force)
$ErrorActionPreference = "Stop"
function Have-Choco { Get-Command choco -ErrorAction SilentlyContinue }
function Have-Winget { Get-Command winget -ErrorAction SilentlyContinue }
Write-Host "Checking cloudflared presence..."
$cf = Get-Command cloudflared -ErrorAction SilentlyContinue
if ($cf -and -not $Force) {
    Write-Host "cloudflared already present: $($cf.Source)"; cloudflared --version; exit 0
}
if (Have-Choco) { choco install cloudflared -y --no-progress }
elseif (Have-Winget) { winget install --id Cloudflare.cloudflared -e --accept-package-agreements --accept-source-agreements }
else { Write-Warning "No choco/winget. Install manually: Cloudflare docs"; exit 1 }
$cf2 = Get-Command cloudflared -ErrorAction SilentlyContinue
if (-not $cf2) { throw "cloudflared not found after install" }
cloudflared --version
Write-Host "Install/Update complete."
