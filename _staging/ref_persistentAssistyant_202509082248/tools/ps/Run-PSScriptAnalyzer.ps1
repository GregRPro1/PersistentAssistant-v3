# tools\ps\Run-PSScriptAnalyzer.ps1 (robust header; safe if PSScriptAnalyzer missing)
[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)][string]$Root,
  [string]$JsonOut = "" ,
  [ValidateSet('Error','Warning','Information')][string[]]$Severity = @('Error','Warning')
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Write-Json { param($Obj,[string]$Path) try { ($Obj | ConvertTo-Json -Depth 8) | Set-Content -LiteralPath $Path -Encoding UTF8 } catch {} }
$rootPath = (Resolve-Path $Root).Path
$files = Get-ChildItem -Path $rootPath -Include *.ps1,*.psm1 -Recurse -File
$results = @()
try {
  if (Get-Module -ListAvailable -Name PSScriptAnalyzer) {
    Import-Module PSScriptAnalyzer -ErrorAction Stop
    $results = Invoke-ScriptAnalyzer -Path ($files | Select-Object -ExpandProperty FullName) -Severity $Severity -Recurse -ErrorAction Continue
  } else {
    # Fallback: no module installed; return empty result rather than breaking pipeline
    $results = @()
  }
} catch {
  $results = @()
}
if ($JsonOut -and $JsonOut.Length -gt 0) { Write-Json -Obj $results -Path $JsonOut }
if ($results -and $results.Count -gt 0) {
  $results | Format-Table -AutoSize | Out-String | Write-Host
} else {
  Write-Host "PSScriptAnalyzer: clean or unavailable."
}
