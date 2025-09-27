
param([Parameter(Mandatory=$true)][string]$ZipPath,[string]$RepoRoot="")
$ErrorActionPreference='Stop'
function Fail($m){ Write-Error $m; exit 1 }
function Exec([string]$c){ Write-Host ">> $c"; $p=Start-Process -NoNewWindow -FilePath "powershell" -ArgumentList "-NoProfile","-ExecutionPolicy Bypass","-Command",$c -PassThru -Wait; if($p.ExitCode -ne 0){ throw "Command failed: $c" } }
function FindRoot($s){ $d=Get-Item $s; for(;;){ if(Test-Path (Join-Path $d.FullName ".git")){return $d.FullName}; if($d.Parent -eq $null){break}; $d=$d.Parent}; return $null }
if(-not $RepoRoot -or -not (Test-Path (Join-Path $RepoRoot ".git"))){ $cand=FindRoot $PSScriptRoot; if($cand){$RepoRoot=$cand} }
if(-not $RepoRoot -or -not (Test-Path (Join-Path $RepoRoot ".git"))){ $def="C:\_Repos\PersistentAssistant"; if(Test-Path (Join-Path $def ".git")){$RepoRoot=$def} }
if(-not $RepoRoot -or -not (Test-Path (Join-Path $RepoRoot ".git"))){ Fail "Repo root not found." }
Set-Location $RepoRoot
Unblock-File -Path $ZipPath -ErrorAction SilentlyContinue
Expand-Archive -Path $ZipPath -DestinationPath $RepoRoot -Force
$apply="scripts\apply_pack.ps1"
if(Test-Path $apply){ & $apply; exit $LASTEXITCODE }
$runner="tools\ps1\run_smoke.ps1"
if(Test-Path $runner){
  $ds=Get-ChildItem -Path (Join-Path $RepoRoot "dev_steps") -Directory -ErrorAction SilentlyContinue
  if(-not $ds){ Fail "No dev_steps/* found" }
  $StepId=$ds[0].Name
  & $runner -StepId $StepId
  exit $LASTEXITCODE
}
Fail "No apply or smoke runner found after extraction."
