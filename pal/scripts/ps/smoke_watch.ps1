param(
  [int]$IntervalSec = 5
)
# Watches reports/smoke for changes and flips statuses accordingly (PASS->review, FAIL->blocked).
# Enqueues a tracker restart when updates occur.
$python = "$env:VIRTUAL_ENV\Scripts\python.exe"; if (-not (Test-Path $python)) { $python = "python" }
$dir = ".\reports\smoke"
$last = @{}
while ($true) {
  try {
    if (Test-Path $dir) {
      $files = Get-ChildItem $dir -Filter *.json -File | Sort-Object LastWriteTime
      $changed = $false
      foreach ($f in $files) {
        $sig = "{0}|{1}" -f $f.FullName, $f.LastWriteTimeUtc.Ticks
        if (-not $last.ContainsKey($f.FullName) -or $last[$f.FullName] -ne $sig) { $changed = $true; $last[$f.FullName] = $sig }
      }
      if ($changed) {
        & $python ".\pal\scripts\py\pal_update_status_from_smoke.py" | Out-Null
        # restart tracker for UI refresh
        $reqDir = ".\pal\control\requests"; if (-not (Test-Path $reqDir)) { New-Item -ItemType Directory -Force -Path $reqDir | Out-Null }
        $req = Join-Path $reqDir ("{0}.json" -f (Get-Date -Format "yyyyMMdd_HHmmss_fff"))
        '{"command":"restart","target":"tracker","note":"smoke watcher updated statuses"}' | Set-Content $req -Encoding UTF8
      }
    }
  } catch {}
  Start-Sleep -Seconds $IntervalSec
}
