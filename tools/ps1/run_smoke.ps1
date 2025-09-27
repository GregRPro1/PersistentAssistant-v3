param(
  [Parameter(Mandatory=$true)][string]$StepId,
  [string]$Py = "",
  [string]$ExtraPytestArgs = "-q"
)
$ErrorActionPreference='Stop'
function Fail($m){ Write-Error $m; exit 1 }
function RunGit([string[]]$args){
  & git @args
  if ($LASTEXITCODE -ne 0) { Fail "git $($args -join ' ') failed ($LASTEXITCODE)" }
}
function TryGitCommit([string]$msg){
  & git commit -m $msg
  if ($LASTEXITCODE -ne 0) { Write-Host "git commit (no changes?): $msg" }
}
function Ensure-Python {
  if ($Py) { return $Py }
  try { & python -V | Out-Null; return "python" } catch {}
  try { & py -3 -V | Out-Null; return "py -3" } catch {}
  Fail "Python not found"
}

if(-not (Test-Path ".git")){ Fail "Run from repo root" }
$Py = Ensure-Python

try { & $Py -c "import yaml,pytest" | Out-Null } catch {
  & $Py -m pip install --upgrade pip
  & $Py -m pip install pyyaml pytest
}

$results = Join-Path (Join-Path "dev_steps" $StepId) "results"
New-Item -ItemType Directory -Force $results | Out-Null
$ts = Get-Date -Format 'yyyyMMdd_HHmm'
$junit = Join-Path $results ("junit_" + $ts + ".xml")
$log   = Join-Path $results ("pytest_" + $ts + ".log")

& $Py -m pytest "tests/smoke" "--junitxml=$junit" $ExtraPytestArgs *>> $log
$pytestCode = $LASTEXITCODE

$zip = Join-Path $results ("smoke_" + $ts + ".zip")
if (Test-Path $zip) { Remove-Item $zip -Force }
Add-Type -AssemblyName 'System.IO.Compression.FileSystem'
$z = [System.IO.Compression.ZipFile]::Open($zip,[System.IO.Compression.ZipArchiveMode]::Create)
foreach($f in @($junit,$log)) { if (Test-Path $f) { [System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile($z,(Resolve-Path $f).Path,[System.IO.Path]::GetFileName($f)) } }
$z.Dispose()

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
