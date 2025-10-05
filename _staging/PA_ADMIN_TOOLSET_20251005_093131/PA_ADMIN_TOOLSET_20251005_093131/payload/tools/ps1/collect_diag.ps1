
$stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$zip = "tmp\logs\diag_bundle_$stamp.zip"
$files = @(
  'tmp\logs\server.out.log',
  'tmp\logs\server.err.log',
  'tmp\logs\cloudflared.out.log',
  'tmp\logs\cloudflared.err.log',
  'reports\ops\watchdog_status.json',
  'reports\ops\tunnel_url.txt',
  'reports\ops\phone_watchdog_url.txt',
  'tmp\logs\diag_status.json',
  'tmp\logs\deep_smoke_result.json'
) | Where-Object { Test-Path $_ }

if (-not $files) { Write-Host "Nothing to zip."; exit 0 }
if (-not (Test-Path 'tmp\logs')) { New-Item -ItemType Directory -Force 'tmp\logs' | Out-Null }
if (Test-Path $zip) { Remove-Item $zip -Force }
Compress-Archive -Path $files -DestinationPath $zip -Force
Write-Host ("Saved {0}" -f $zip)
