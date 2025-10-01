param([Parameter(Mandatory=$true)][string]$Name)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
function Try-ApiRestart {
  try {
    $url = "http://127.0.0.1:8776/api/watchdog/$Name/restart"
    $r = Invoke-RestMethod -Method Post -Uri $url -TimeoutSec 5 -ErrorAction Stop
    if ($r.ok) { Write-Host "API restart issued for $Name"; return $true }
  } catch {}
  return $false
}
if (Try-ApiRestart) { exit 0 }
$stFile = "reports\ops\watchdog_status.json"
if (-not (Test-Path $stFile)) { Write-Host "no status file, cannot fallback"; exit 2 }
try { $json = Get-Content $stFile -Raw | ConvertFrom-Json } catch { Write-Host "bad json in $stFile"; exit 3 }
$p = $json.processes.$Name
if (-not $p -or -not $p.pid) { Write-Host "unknown process or no pid"; exit 4 }
try { taskkill /PID ([int]$p.pid) /T /F | Out-Null; Write-Host "killed $Name (PID $($p.pid))"; exit 0 } catch { exit 5 }
