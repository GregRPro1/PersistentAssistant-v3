$ErrorActionPreference='Stop'
& python (Join-Path $PSScriptRoot 'apply_pack.py')
exit $LASTEXITCODE
