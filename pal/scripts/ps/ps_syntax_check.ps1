# pal/scripts/ps/ps_syntax_check.ps1
Set-StrictMode -Version Latest
$ErrorActionPreference = "Continue"

param([string]$Path = ".\pal\core\health\watchdog.ps1")

$tokens = $null; $errors = $null
[void][System.Management.Automation.Language.Parser]::ParseFile($Path, [ref]$tokens, [ref]$errors)
if ($errors -and $errors.Count -gt 0) {
  Write-Host "SYNTAX FAIL in $Path" -ForegroundColor Red
  $errors | ForEach-Object { Write-Host (" - {0}" -f $_.Message) -ForegroundColor Red }
  exit 1
} else {
  Write-Host "SYNTAX OK: $Path" -ForegroundColor Green
}
