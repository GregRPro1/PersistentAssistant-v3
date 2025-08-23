param(
  [Parameter(ValueFromRemainingArguments=$true)]
  [string[]]$Args
)
Write-Host "[PRE] Running forbidden guard (warn-only)..." -ForegroundColor Cyan
powershell -NoProfile -ExecutionPolicy Bypass -File tools\guard_run.ps1 | Write-Host

Write-Host "`n[DO] apply_and_pack.py $Args" -ForegroundColor Cyan
$py = Join-Path (Get-Location) "tools\apply_and_pack.py"
if (!(Test-Path $py)) {
  Write-Host "[ERR] tools\apply_and_pack.py not found." -ForegroundColor Red
  exit 1
}
python $py @Args
