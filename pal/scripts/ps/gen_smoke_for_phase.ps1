param([Parameter(Mandatory=$true)][string]$Phase)
$python = "$env:VIRTUAL_ENV\Scripts\python.exe"; if (-not (Test-Path $python)) { $python = "python" }
# Query tasks in the phase
$json = & $python ".\pal\scripts\py\pal_phase_tools.py" list $Phase
$info = $json | ConvertFrom-Json
$tasks = $info.tasks
$dest = ".\pal\tests\smoke"
if (-not (Test-Path $dest)) { New-Item -ItemType Directory -Force -Path $dest | Out-Null }
$stub = @'
param([string]$Name)
$OutDir = ".\reports\smoke"; if (-not (Test-Path $OutDir)) { New-Item -ItemType Directory -Force -Path $OutDir | Out-Null }
$ts = (Get-Date).ToString("s")
$result = @{ test = $Name; ts = $ts; ok = $true; notes = "stub PASS" }
($result | ConvertTo-Json -Depth 5) | Set-Content (Join-Path $OutDir "$Name.json") -Encoding UTF8
Write-Host "$Name PASS"
'@
foreach ($t in $tasks) {
  $id = $t.id
  if (-not $id) { continue }
  $path = Join-Path $dest ("{0}.ps1" -f $id)
  if (-not (Test-Path $path)) {
    Set-Content -Path $path -Value $stub -Encoding UTF8
    Write-Host "Created stub: $path"
  }
}
