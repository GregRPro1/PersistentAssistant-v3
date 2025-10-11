param([string]$Message = "PAL: plan update")
git add .\pal\plan\pal_project_plan.yaml | Out-Null
if (Test-Path .\reports\smoke) { git add .\reports\smoke\*.json -A -f | Out-Null }
git commit -m $Message
