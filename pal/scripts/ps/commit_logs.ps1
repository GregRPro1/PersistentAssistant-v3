Set-StrictMode -Version Latest
$ErrorActionPreference = "Continue"
git add .\tmp\logs\*.log* -f 2>$null
git add .\reports\ops\*.json -f 2>$null
git add .\reports\smoke\*.json -f 2>$null
try { git commit -m "PAL: commit diagnostics and smoke logs" } catch {}
Write-Host "Committed diagnostics and smoke logs (if changes were present)."