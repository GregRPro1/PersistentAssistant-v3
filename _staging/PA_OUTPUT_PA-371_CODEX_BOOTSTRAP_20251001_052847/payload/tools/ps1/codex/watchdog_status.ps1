Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$stFile = "reports\ops\watchdog_status.json"
if (-not (Test-Path $stFile)) { Write-Host "no status file ($stFile)"; exit 2 }
try { $json = Get-Content $stFile -Raw | ConvertFrom-Json } catch { Write-Host "bad json in $stFile"; exit 3 }
$age = if ($json._file_age_s) { [int]$json._file_age_s } else { 999999 }
"{0,-10} {1,-8} {2}" -f "PROCESS","STATE","PID"
foreach ($k in $json.processes.PSObject.Properties.Name) {
  $p = $json.processes.$k
  "{0,-10} {1,-8} {2}" -f $k, ($p.state ?? "n/a"), ($p.pid ?? "—")
}
"updated {0}s ago" -f $age
