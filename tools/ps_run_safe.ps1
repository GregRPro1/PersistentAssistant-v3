param([Parameter(Mandatory=$true)][string]$Path)
$ErrorActionPreference='Stop'
$logDir = "tmp\logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$logGuard = Join-Path $logDir "forbidden_$stamp.txt"

# 1) PS syntax preflight
& powershell -NoProfile -ExecutionPolicy Bypass -File "tools\ps_parse_preflight.ps1" -Path $Path 2>&1 | Tee-Object -FilePath (Join-Path $logDir "ps_syntax_$stamp.txt")
if ($LASTEXITCODE -ne 0) {
  Write-Host "[PRE] PowerShell syntax errors. See tmp\logs\ps_syntax_$stamp.txt"
  exit 2
}

# 2) Forbidden guard (warn-only)
python tools\forbidden_guard.py --warn > $logGuard 2>&1
Write-Host "[PRE] Guard rc=$LASTEXITCODE — continuing (warn-only). Log: $logGuard"

# 3) Execute script
& powershell -NoProfile -ExecutionPolicy Bypass -File $Path
exit $LASTEXITCODE
