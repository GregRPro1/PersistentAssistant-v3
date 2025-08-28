# Persistent Assistant — Thin PS runner (robust) that delegates to Python diag, then prints endpoints and footer
# ID: PA_20250826-switch-to-python-tools-v2.1

[CmdletBinding()]
param(
  [ValidateSet('quiet','normal','verbose')]
  [string]$Verbosity = 'normal'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Ensure-Dir { param([string]$Path) if (-not (Test-Path -LiteralPath $Path)) { New-Item -ItemType Directory -Path $Path | Out-Null } }

# Paths and staging
$repoRoot = (Get-Location).Path
Ensure-Dir "tmp"; Ensure-Dir "tmp\run"
$stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$diagJson = Join-Path $repoRoot ("tmp\run\diag_{0}.json" -f $stamp)
$outLog   = Join-Path $repoRoot ("tmp\run\pa_diag_runner_{0}.out.log" -f $stamp)
$errLog   = Join-Path $repoRoot ("tmp\run\pa_diag_runner_{0}.err.log" -f $stamp)

# 1) Run Python diag via Start-Process; capture stdout/stderr to files
$startInfo = @{
  FilePath               = "python"
  ArgumentList           = @(".\tools\py\pa_diag_runner.py","--out",$diagJson)
  WorkingDirectory       = $repoRoot
  NoNewWindow            = $true
  PassThru               = $true
  RedirectStandardOutput = $outLog
  RedirectStandardError  = $errLog
}
$proc = $null
try { $proc = Start-Process @startInfo; $proc.WaitForExit() } catch {}

# 2) Read diag result if present
$packPath = "[NOT CREATED]"
$status   = "FAIL diag_failed"
if (Test-Path -LiteralPath $diagJson) {
  try {
    $diag = Get-Content -LiteralPath $diagJson -Raw | ConvertFrom-Json
    if ($diag -and ($diag.PSObject.Properties.Name -contains 'pack_path')) { $packPath = '' + $diag.pack_path }
    if ($diag -and ($diag.PSObject.Properties.Name -contains 'status'))    { $status   = '' + $diag.status }
  } catch {}
}

# 3) Run auto health and print explicit OK/FAIL per endpoint
$healthJson = Join-Path $repoRoot ("tmp\run\auto_health_{0}.json" -f $stamp)
$health = $null
try {
  & ".\tools\auto_health.ps1" -JsonOut $healthJson | Out-Null
  if (Test-Path -LiteralPath $healthJson) { $health = Get-Content -LiteralPath $healthJson -Raw | ConvertFrom-Json }
} catch {}

if ($health) {
  $eps = @()
  if ($health.PSObject.Properties.Name -contains 'results'   -and $health.results)   { $eps = @($health.results) }
  elseif ($health.PSObject.Properties.Name -contains 'endpoints' -and $health.endpoints) { $eps = @($health.endpoints) }
  foreach ($e in $eps) {
    $name  = '' + $e.name
    $state = 'FAIL'
    if ($e.PSObject.Properties.Name -contains 'ok') { if ([bool]$e.ok) { $state = 'OK' } }
    Write-Host ("ENDPOINT {0}: {1}" -f $name, $state)
  }
}

# 4) Footer (exactly three lines) — always prints, no execution
"PACK: $packPath"
"STATUS: $status"
"python ./tools/show_next_step.py"
