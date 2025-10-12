$ErrorActionPreference='Stop'
$master="PAL20251012"
$child="PAL20251012B_SMOKE2"
pwsh .\tools\context\context_capture.ps1 -MasterId $master -ChildId $child -Notes "SMOKE2 TEST"
pwsh .\tools\context\context_loader.ps1  -MasterId $master
pwsh .\tools\context\context_close.ps1   -MasterId $master -ChildId $child -Notes "SMOKE2 CLOSED"
Write-Host "Smoke2 OK at _context\$child"
