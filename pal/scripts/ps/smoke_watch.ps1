param([int]$IntervalSec = 5)
$python = "$env:VIRTUAL_ENV\Scripts\python.exe"; if (-not (Test-Path $python)) { $python = "python" }
$dir = ".\reports\smoke"
$hb  = Join-Path $dir "_watcher_heartbeat.txt"
if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }
$last = @{}
function Read-Yaml {
  param([string]$p)
  try {
    $raw = Get-Content -Raw $p -ErrorAction Stop
    $y = ConvertFrom-Yaml $raw
    return $y
  } catch { return $null }
}
while ($true) {
  try {
    (Get-Date).ToString("s") | Set-Content $hb -Encoding UTF8
    $files = Get-ChildItem $dir -Filter *.json -File -ErrorAction SilentlyContinue | Sort-Object LastWriteTime
    $changed = $false
    foreach ($f in $files) {
      $sig = "{0}|{1}" -f $f.FullName, $f.LastWriteTimeUtc.Ticks
      if (-not $last.ContainsKey($f.FullName) -or $last[$f.FullName] -ne $sig) { $changed = $true; $last[$f.FullName] = $sig }
    }
    if ($changed) {
      # Update plan statuses, but do not downgrade done -> review
      $planPath = ".\pal\plan\pal_project_plan.yaml"
      if (-not (Test-Path $planPath)) { $planPath = ".\project\plans\project_plan_v3.yaml" }
      if (Test-Path $planPath) {
        $plan = Read-Yaml $planPath
        if ($plan) {
          $updated = $false
          foreach ($ph in $plan.phases) {
            foreach ($t in $ph.tasks) {
              $tid = [string]$t.id
              $jf = Join-Path $dir "$tid.json"
              if (Test-Path $jf) {
                $data = Get-Content -Raw $jf | ConvertFrom-Json
                if ($data.ok -eq $true) {
                  if ($t.status -ne "done") {
                    # only set to review if not already done
                    if ($t.status -ne "review") { $t.status = "review"; $updated = $true }
                  }
                } else {
                  $t.status = "blocked"; $updated = $true
                }
              }
            }
          }
          if ($updated) {
            $yaml = $plan | ConvertTo-Yaml
            Set-Content $planPath $yaml -Encoding UTF8
            # ask tracker to restart and commit
            $reqDir = ".\pal\control\requests"; if (-not (Test-Path $reqDir)) { New-Item -ItemType Directory -Force -Path $reqDir | Out-Null }
            $req = Join-Path $reqDir ("{0}.json" -f (Get-Date -Format "yyyyMMdd_HHmmss_fff"))
            '{"command":"restart","target":"tracker","note":"smoke watcher update"}' | Set-Content $req -Encoding UTF8
            $req2 = Join-Path $reqDir ("{0}_commit.json" -f (Get-Date -Format "yyyyMMdd_HHmmss_fff"))
            '{"command":"commit_plan","message":"PAL: auto-update from smoke watcher"}' | Set-Content $req2 -Encoding UTF8
          }
        }
      }
    }
  } catch {}
  Start-Sleep -Seconds $IntervalSec
}
