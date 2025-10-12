Set-StrictMode -Version Latest
$ErrorActionPreference = "Continue"
function Ensure-Dir([string]$p){ if (-not (Test-Path $p)) { New-Item -ItemType Directory -Force -Path $p | Out-Null } }
function Write-Log([string]$File, [string]$Level, [string]$Message){
  try {
    $dir = Split-Path -Parent $File; Ensure-Dir $dir
    if (Test-Path $File) {
      $size = (Get-Item $File).Length
      if ($size -gt 2MB) { $ts = Get-Date -Format "yyyyMMdd_HHmmss"; Copy-Item $File "$File.$ts.bak" -ErrorAction SilentlyContinue; Clear-Content $File -ErrorAction SilentlyContinue }
    }
    $ts = Get-Date -Format "s"
    Add-Content -Path $File -Value ("{0} [{1}] {2}" -f $ts, $Level.ToUpper(), $Message)
  } catch {}
}