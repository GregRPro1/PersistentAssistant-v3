# tools\ps\Test-PSScripts.ps1 (robust)
[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)][string]$Root,
  [string]$JsonOut
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Write-Json { param($Obj, [string]$Path)
  try {
    $dir = Split-Path -Parent $Path
    if ($dir -and -not (Test-Path -LiteralPath $dir)) { New-Item -ItemType Directory -Path $dir | Out-Null }
    ($Obj | ConvertTo-Json -Depth 8) | Set-Content -LiteralPath $Path -Encoding UTF8
  } catch {}
}

$results = New-Object System.Collections.Generic.List[object]
try {
  $rootPath = (Resolve-Path $Root).Path
  $files = Get-ChildItem -Path $rootPath -Include *.ps1,*.psm1 -Recurse -File
  foreach ($f in $files) {
    $tokens = $null; $errors = $null
    [void][System.Management.Automation.Language.Parser]::ParseFile($f.FullName, [ref]$tokens, [ref]$errors)
    if ($errors) {
      foreach ($e in $errors) {
        $results.Add([pscustomobject]@{
          file   = $f.FullName
          line   = $e.Extent.StartLineNumber
          column = $e.Extent.StartColumnNumber
          message= $e.Message
          snippet= $e.Extent.Text
        })
      }
    }
  }
  if ($JsonOut) { Write-Json -Obj $results -Path $JsonOut }
  if ($results.Count -gt 0) {
    $results | Sort-Object file,line | Format-Table -AutoSize | Out-String | Write-Host
    throw "Parse errors found in $($results.Count) location(s)."
  }
  Write-Host "All PowerShell files parsed cleanly."
} catch {
  if ($results.Count -eq 0) {
    $em = @([pscustomobject]@{
      file   = "[gate]"
      line   = 0
      column = 0
      message= $_.Exception.Message
      snippet= ""
    })
    if ($JsonOut) { Write-Json -Obj $em -Path $JsonOut }
  } else {
    if ($JsonOut) { Write-Json -Obj $results -Path $JsonOut }
  }
  throw
}
