param(
  [string]$Root = "."
)
$ts = Get-Date -Format "yyyyMMdd_HHmmss"
$report = "tmp\logs\guard_report_{0}.json" -f $ts

# Run guard and capture rc
$ps = Start-Process -FilePath "powershell" -ArgumentList "-NoProfile","-ExecutionPolicy","Bypass","-File","tools\gentle_guard.ps1","-Root",$Root,"-OutJson",$report -PassThru -Wait -WindowStyle Hidden
$rc = $ps.ExitCode

Write-Host "`n[GUARD] ExitCode=$rc  Report=$(Resolve-Path $report)"

if ($rc -ne 0) {
  try {
    $viol = Get-Content -Raw -ErrorAction SilentlyContinue $report | ConvertFrom-Json
    if ($viol) {
      Write-Host "[GUARD] Violations:" -ForegroundColor Yellow
      foreach ($v in $viol) {
        $s = $v.sample
        if ($s -and $s.Length -gt 80) { $s = $s.Substring(0,80) + "..." }
        Write-Host " - $($v.file)`n   pattern: $($v.pattern)`n   sample: $s"
      }
    } else {
      Write-Host "[GUARD] Violations present but report unreadable."
    }
  } catch {
    Write-Host "[GUARD] Could not parse report: $($_.Exception.Message)"
  }
}
# Always exit 0 here (warn-but-continue)
exit 0
