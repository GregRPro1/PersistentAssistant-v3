param(
  [string]$PlanPath = ".\pal\plan\pal_project_plan.yaml",
  [switch]$NoInstall
)

$python = "$env:VIRTUAL_ENV\Scripts\python.exe"
if (-not (Test-Path $python)) { $python = "python" }

if (-not $NoInstall) {
  & pip install -r ".\pal\ui\desktop\requirements.txt"
}

& $python ".\pal\ui\desktop\pal_tracker.py" $PlanPath
