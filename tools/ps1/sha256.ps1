param([Parameter(Mandatory=$true)][string]$Path)
$ErrorActionPreference='Stop'
if (-not (Test-Path $Path)) { Write-Error "not found: $Path" }
$root = (Get-Location).Path
& python (Join-Path $root 'tools\py\sha256sum.py') $Path
exit $LASTEXITCODE
