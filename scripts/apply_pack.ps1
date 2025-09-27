param(
  [string]$RepoRoot = "",
  [string]$StepId   = "PA-102",
  [string]$StepSlug = "plan-update"
)
$ErrorActionPreference = 'Stop'

function Fail($m){ Write-Error $m; exit 1 }
function FindRoot([string]$start){
  $d = Get-Item $start
  for(;;){
    if (Test-Path (Join-Path $d.FullName ".git")) { return $d.FullName }
    if ($d.Parent -eq $null) { break }
    $d = $d.Parent
  }
  return $null
}
function RunGit([string[]]$args){
  & git @args
  if ($LASTEXITCODE -ne 0) { Fail "git $($args -join ' ') failed ($LASTEXITCODE)" }
}
function TryGitCommit([string]$msg){
  & git commit -m $msg
  if ($LASTEXITCODE -ne 0) { Write-Host "git commit (no changes?): $msg" }
}
function Ensure-Python {
  try { & python -V | Out-Null; return "python" } catch {}
  try { & py -3 -V | Out-Null; return "py -3" } catch {}
  Fail "Python 3 not found"
}

# Resolve repo root
if (-not $RepoRoot -or -not (Test-Path (Join-Path $RepoRoot ".git"))) {
  $cand = FindRoot $PSScriptRoot
  if ($cand) { $RepoRoot = $cand }
}
if (-not $RepoRoot -or -not (Test-Path (Join-Path $RepoRoot ".git"))) {
  $def = "C:\_Repos\PersistentAssistant"
  if (Test-Path (Join-Path $def ".git")) { $RepoRoot = $def }
}
if (-not $RepoRoot -or -not (Test-Path (Join-Path $RepoRoot ".git"))) {
  Fail "Repo root not found. Unzip pack at repo root."
}
Set-Location $RepoRoot

$ts = Get-Date -Format 'yyyyMMdd_HHmm'
$branch = "step/$StepId-$StepSlug"

# Branch
$exists = ((git branch --list $branch) | Measure-Object).Count -gt 0
if (-not $exists) { RunGit @('checkout','-b',$branch) } else { RunGit @('checkout',$branch) }

# Stage files then initial commit
$toStage = @(
  "dev_steps/$StepId",
  "tools/py/plan_merge.py",
  "dev_steps/PA-102/plan_steps_to_add.yaml",
  "tests/smoke/test_plan_includes_devsteps.py",
  "scripts/apply_pack.ps1"
) | Where-Object { Test-Path $_ }
if ($toStage.Count -gt 0) { RunGit @('add') + $toStage }
TryGitCommit "$($StepId): add plan merge tool, steps, smoke"

# Python deps
$Py = Ensure-Python
try { & $Py -c "import yaml" | Out-Null } catch {
  & $Py -m pip install --upgrade pip
  & $Py -m pip install pyyaml
}

# Merge plan
$plan = "project/plans/project_plan_v3.yaml"
& $Py "tools/py/plan_merge.py" $plan "dev_steps/PA-102/plan_steps_to_add.yaml"
if ($LASTEXITCODE -ne 0) { Fail "plan_merge failed" }
RunGit @('add',$plan)
TryGitCommit "$($StepId): merge dev_steps into plan @ $ts"
RunGit @('push','-u','origin',$branch)

# Smoke deps
try { & $Py -c "import pytest, yaml" | Out-Null } catch {
  & $Py -m pip install pytest pyyaml
}

# Run smoke
$results = Join-Path (Join-Path "dev_steps" $StepId) "results"
New-Item -ItemType Directory -Force $results | Out-Null
$junit = Join-Path $results ("junit_" + $ts + ".xml")
$log   = Join-Path $results ("pytest_" + $ts + ".log")
$zip   = Join-Path $results ("smoke_" + $ts + ".zip")

& $Py -m pytest "tests/smoke/test_plan_includes_devsteps.py" "--junitxml=$junit" "-q" *>> $log
$pytestCode = $LASTEXITCODE

Add-Type -AssemblyName 'System.IO.Compression.FileSystem'
$z = [System.IO.Compression.ZipFile]::Open($zip,[System.IO.Compression.ZipArchiveMode]::Create)
foreach($f in @($junit,$log)) { if (Test-Path $f) { [System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile($z,(Resolve-Path $f).Path,[System.IO.Path]::GetFileName($f)) } }
$z.Dispose()

# Manifest update
$manifest = Join-Path (Join-Path "dev_steps" $StepId) "manifest.yaml"
$status = if ($pytestCode -eq 0) { "pass" } else { "fail" }
$sha = (git rev-parse HEAD).Trim()
$relZip = (Resolve-Path $zip).Path.Replace((Resolve-Path ".").Path + '\','').Replace('\','/')

$block = @"
# updated smoke at $ts
latest:
  smoke_zip: "$relZip"
  status: "$status"
  commit_sha: "$sha"
  updated_at: "$ts"
"@
Add-Content -Path $manifest -Value $block

RunGit @('add', $results, $manifest)
TryGitCommit "$($StepId): publish smoke ($status) @ $ts"
RunGit @('push')

Write-Host "PA-102 done."
