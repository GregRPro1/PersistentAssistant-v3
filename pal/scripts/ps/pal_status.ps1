param(
  [string]$PlanPath = ".\pal\plan\pal_project_plan.yaml",
  [string]$Phase,            # e.g., "M0" to filter one phase
  [int]$Top = 10,
  [switch]$Json
)

if (-not (Test-Path $PlanPath)) {
  Write-Error "Plan not found: $PlanPath"
  exit 1
}

$lines = Get-Content -LiteralPath $PlanPath -Encoding UTF8

# Very small YAML reader tailored to our plan structure.
# It assumes the indentation/layout we shipped.
$projectName = ""
$version = ""
$goals = @()
$phases = @()

$inGoals = $false
$inPhases = $false
$currentPhase = $null
$inTasks = $false

function Flush-Phase {
  param($phase)
  if ($null -ne $phase) { $script:phases += $phase }
}

foreach ($raw in $lines) {
  $line = $raw.TrimEnd()

  if ($line -match '^\s*name:\s*(.+)$' -and -not $projectName) {
    $projectName = ($Matches[1]).Trim()
    continue
  }
  if ($line -match '^\s*version:\s*(.+)$' -and -not $version) {
    $version = ($Matches[1]).Trim()
    continue
  }

  if ($line -match '^\s*goals:\s*$') {
    $inGoals = $true; $inPhases = $false; continue
  }
  if ($inGoals -and $line -match '^\s*-\s*"(.*)"\s*$') {
    $goals += $Matches[1]; continue
  }
  if ($inGoals -and $line -match '^\S') {
    $inGoals = $false
  }

  if ($line -match '^\s*phases:\s*$') {
    $inPhases = $true; continue
  }

  if ($inPhases) {
    # Start of a phase block: "  - id: M0"
    if ($line -match '^\s*-\s*id:\s*([A-Za-z0-9_-]+)\s*$') {
      # Flush previous phase
      Flush-Phase $currentPhase
      $currentPhase = [ordered]@{
        id = $Matches[1]
        name = ""
        priority = $null
        tasks = @()
      }
      $inTasks = $false
      continue
    }
    if ($null -ne $currentPhase) {
      if ($line -match '^\s*name:\s*(.+)$' -and -not $currentPhase.name) {
        $currentPhase.name = ($Matches[1]).Trim()
        continue
      }
      if ($line -match '^\s*priority:\s*([0-9]+)\s*$' -and -not $currentPhase.priority) {
        $currentPhase.priority = [int]$Matches[1]
        continue
      }
      if ($line -match '^\s*tasks:\s*$') {
        $inTasks = $true
        continue
      }
      if ($inTasks) {
        # Task entry begins: "      - id: PAL-100"
        if ($line -match '^\s*-\s*id:\s*([A-Za-z0-9_-]+)\s*$') {
          $currentTask = [ordered]@{
            id = $Matches[1]
            title = ""
            status = "todo"
            priority = 3
          }
          $currentPhase.tasks += $currentTask
          continue
        }
        if ($null -ne $currentTask) {
          if ($line -match '^\s*title:\s*(.+)$' -and -not $currentTask.title) {
            $currentTask.title = ($Matches[1]).Trim()
            continue
          }
          if ($line -match '^\s*status:\s*([A-Za-z_]+)\s*$') {
            $currentTask.status = $Matches[1]
            continue
          }
          if ($line -match '^\s*priority:\s*([0-9]+)\s*$') {
            $currentTask.priority = [int]$Matches[1]
            continue
          }
        }
      }
    }
  }
}

Flush-Phase $currentPhase

# Filter by phase if requested
if ($Phase) {
  $phases = $phases | Where-Object { $_.id -eq $Phase }
}

# Flatten tasks
$tasks = foreach ($ph in $phases) {
  foreach ($t in $ph.tasks) {
    [pscustomobject]@{
      phase = $ph.id
      phaseName = $ph.name
      id = $t.id
      title = $t.title
      status = $t.status
      priority = $t.priority
    }
  }
}

if ($Json) {
  [pscustomobject]@{
    project = $projectName
    version = $version
    goals = $goals
    phases = $phases
    tasks = $tasks
  } | ConvertTo-Json -Depth 6
  exit 0
}

function Color($text, $status) {
  switch ($status) {
    "done"         { $c="Green" }
    "in_progress"  { $c="Yellow" }
    "review"       { $c="Cyan" }
    "blocked"      { $c="Red" }
    default        { $c="Gray" }
  }
  Write-Host $text -ForegroundColor $c
}

$total = $tasks.Count
$done  = ($tasks | Where-Object status -eq "done").Count
$prog  = if ($total -gt 0) { [math]::Round(100*$done/$total,0) } else { 0 }

Write-Host ("PAL Status — {0} v{1}" -f $projectName,$version) -ForegroundColor White
Write-Host "Goals:" -ForegroundColor White
foreach ($g in $goals) { Write-Host ("  • {0}" -f $g) -ForegroundColor DarkGray }
Write-Host ""

Write-Host ("Overall: {0}/{1} done ({2}%)" -f $done,$total,$prog) -ForegroundColor White

Write-Host "`nPer phase:" -ForegroundColor White
foreach ($ph in $phases) {
  $ts = $tasks | Where-Object phase -eq $ph.id
  $td = ($ts | Where-Object status -eq "done").Count
  $tt = $ts.Count
  $pp = if ($tt -gt 0) { [math]::Round(100*$td/$tt,0) } else { 0 }
  Write-Host ("  {0,-3} {1,-34} {2}/{3} ({4}%)" -f $ph.id, $ph.name, $td, $tt, $pp) -ForegroundColor White
}

$ip = $tasks | Where-Object status -eq "in_progress"
if ($ip) {
  Write-Host "`nIn progress:" -ForegroundColor White
  foreach ($t in $ip) { Color ("  - [{0}] {1}: {2}" -f $t.phase,$t.id,$t.title) "in_progress" }
}

$bl = $tasks | Where-Object status -eq "blocked"
if ($bl) {
  Write-Host "`nBlocked:" -ForegroundColor White
  foreach ($t in $bl) { Color ("  - [{0}] {1}: {2}" -f $t.phase,$t.id,$t.title) "blocked" }
}

$next = $tasks | Where-Object { $_.status -in @("todo","review") } | Sort-Object priority, id | Select-Object -First $Top
if ($next) {
  Write-Host ("`nNext actions (top {0}):" -f $Top) -ForegroundColor White
  foreach ($t in $next) {
    $s = if ($t.status -eq "review") { "review" } else { "todo" }
    Color ("  - (P{0}) [{1}] {2}: {3}" -f $t.priority,$t.phase,$t.id,$t.title) $s
  }
}

Write-Host "`nTree:" -ForegroundColor White
foreach ($ph in $phases) {
  Write-Host ("└─ {0} {1}" -f $ph.id, $ph.name) -ForegroundColor White
  foreach ($t in $tasks | Where-Object phase -eq $ph.id) {
    Color ("   ├─ {0,-11} [{1}] {2}" -f $t.status, $t.id, $t.title) $t.status
  }
}
