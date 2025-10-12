param([Parameter(Mandatory=$true)][string]$MasterId)
$ErrorActionPreference='Stop'
$repo = git rev-parse --show-toplevel 2>$null; if (-not $repo){$repo="C:\_Repos\PersistentAssistant"}
$repo = [System.IO.Path]::GetFullPath($repo)
$masterDir = Join-Path $repo ("_context\"+$MasterId)
$indexYaml = Join-Path $masterDir "index.yaml"
$activeYaml = Join-Path $repo "_context\active_context.yaml"
if (-not (Test-Path $masterDir)){ New-Item -ItemType Directory -Force -Path $masterDir | Out-Null }
$lastChild = $null
if (Test-Path $indexYaml){
  Get-Content $indexYaml | ForEach-Object { if ($_ -match '^\s*last_child\s*:\s*(\S+)'){$script:lastChild=$Matches[1]} }
}
$now = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
@("master_id: $MasterId","last_child: $lastChild","loaded_at: $now") | Set-Content $activeYaml -Encoding UTF8
$env:PAL_MASTER=$MasterId; if($lastChild){$env:PAL_CHILD=$lastChild}
Write-Host "Loaded master: $MasterId; last_child: $lastChild"; Write-Host "Active: $activeYaml"
