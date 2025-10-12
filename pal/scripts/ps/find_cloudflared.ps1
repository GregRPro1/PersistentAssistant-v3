param([switch]$InstallIfMissing)
Set-StrictMode -Version Latest
$ErrorActionPreference = "Continue"
function Try-Path([string]$p){ if ($p -and (Test-Path $p)) { return (Resolve-Path $p).Path } return $null }
$envExe = $env:CLOUDFLARED_EXE; if ($envExe) { $ex = Try-Path $envExe; if ($ex) { Write-Output $ex; exit 0 } }
$cfgPath = ".\pal\config\pal_watchdog.json"
try { if (Test-Path $cfgPath) { $cfg = Get-Content -Raw $cfgPath | ConvertFrom-Json; if ($cfg.cloudflared -and $cfg.cloudflared.path) { $ex = Try-Path $cfg.cloudflared.path; if ($ex) { Write-Output $ex; exit 0 } } } } catch {}
$inPath = Get-Command cloudflared -ErrorAction SilentlyContinue; if ($inPath -and $inPath.Source) { Write-Output $inPath.Source; exit 0 }
$cands = @("C:\Program Files (x86)\cloudflared\cloudflared.exe","C:\Program Files\cloudflared\cloudflared.exe")
foreach ($c in $cands) { $ex = Try-Path $c; if ($ex) { Write-Output $ex; exit 0 } }
if ($InstallIfMissing) {
  $winget = Get-Command winget -ErrorAction SilentlyContinue
  if ($winget) { try { winget install --id Cloudflare.cloudflared -e --accept-source-agreements --accept-package-agreements -h 0 | Out-Null; $inPath = Get-Command cloudflared -ErrorAction SilentlyContinue; if ($inPath) { Write-Output $inPath.Source; exit 0 } } catch {} }
  $choco = Get-Command choco -ErrorAction SilentlyContinue
  if ($choco) { try { choco install cloudflared -y | Out-Null; $inPath = Get-Command cloudflared -ErrorAction SilentlyContinue; if ($inPath) { Write-Output $inPath.Source; exit 0 } } catch {} }
}
Write-Error "cloudflared not found. Set CLOUDFLARED_EXE or pal\config\pal_watchdog.json -> cloudflared.path, or install with winget/choco."
exit 1