Set-StrictMode -Version Latest
$ErrorActionPreference = "Continue"
function Is-GoodUrl([string]$u) { if (-not $u) { return $false } try { if ([Uri]::IsWellFormedUriString($u, [UriKind]::Absolute)) { $uri = [Uri]$u; return ($uri.Scheme -in @("http","https")) } } catch {}; return $false }
$smokeDir = ".\reports\smoke"; if (-not (Test-Path $smokeDir)) { New-Item -ItemType Directory -Force -Path $smokeDir | Out-Null }
$rec = @{ test="PAL-TUNNEL"; ok=$false; ts=(Get-Date).ToString("s"); steps=@() }
try {
  $path = pwsh -NoProfile -Command ".\pal\scripts\ps\find_cloudflared.ps1"; $rec.steps += "cloudflared path: $path"; if (-not $path) { throw "cloudflared not found" }
  pwsh .\pal\scripts\ps\run_quick_tunnel.ps1 -Port 8787 | Out-Null; Start-Sleep -Seconds 2
  $tun = (Get-Content ".\reports\ops\tunnel_url.txt" -ErrorAction SilentlyContinue | Select-Object -First 1); $rec.steps += "tunnel_url.txt: $tun"
  if (Is-GoodUrl $tun) { $rec.ok = $true }
} catch { $rec.steps += "error: $($_.Exception.Message)" }
$rec | ConvertTo-Json -Depth 6 | Set-Content (Join-Path $smokeDir "PAL-TUNNEL.json") -Encoding UTF8
Write-Host ("PAL-TUNNEL {0}" -f ($(if ($rec.ok) { "PASS" } else { "FAIL" })))