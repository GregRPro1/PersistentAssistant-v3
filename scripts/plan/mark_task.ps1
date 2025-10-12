Param(
  [string]$PlanPath = "C:\_Repos\PersistentAssistant\pal_project_plan.yaml",
  [string]$Id,
  [ValidateSet('NotStarted','InProgress','Done','Blocked')][string]$Status = 'Done'
)
$ErrorActionPreference = "Stop"
if (-not (Test-Path $PlanPath)) { throw "Plan not found: $PlanPath" }
$text = Get-Content $PlanPath -Raw
$lines = $text -split "`r?`n"
function Update-PhaseStatus([string]$pid,[string]$status) {
  $pattern = "^\s*-?\s*id:\s*$pid\s*$"
  for ($i=0; $i -lt $lines.Length; $i++) {
    if ($lines[$i] -match $pattern) {
      for ($j=$i; $j -lt [Math]::Min($i+20, $lines.Length); $j++) {
        if ($lines[$j] -match "^\s*status:\s*\w+") {
          $lines[$j] = ($lines[$j] -replace "^\s*status:\s*\w+","  status: $status"); return
        }
      }
    }
  }
}
function Update-TaskStatus([string]$pid,[string]$tid,[string]$status) {
  $phasePat = "^\s*-?\s*id:\s*$pid\s*$"
  for ($i=0; $i -lt $lines.Length; $i++) {
    if ($lines[$i] -match $phasePat) {
      for ($j=$i; $j -lt [Math]::Min($i+200, $lines.Length); $j++) {
        if ($lines[$j] -match "^\s*tasks:\s*$") {
          for ($k=$j; $k -lt [Math]::Min($j+200, $lines.Length); $k++) {
            if ($lines[$k] -match "^\s*id:\s*$tid\s*$") {
              for ($m=$k; $m -lt [Math]::Min($k+10, $lines.Length); $m++) {
                if ($lines[$m] -match "^\s*status:\s*\w+") {
                  $indent = ($lines[$m] -replace "^(\\s*).*","$1")
                  $lines[$m] = "$indent" + "status: $status"; return
                }
              }
            }
          }
        }
      }
    }
  }
}
if ($Id -match '^\w+\.\w+$') { $parts = $Id -split '\.'; Update-TaskStatus -pid $parts[0] -tid $parts[1] -status $Status } else { Update-PhaseStatus -pid $Id -status $Status }
Set-Content -Path $PlanPath -Value ($lines -join "`r`n") -Encoding UTF8
Write-Host "Updated $Id -> $Status"
