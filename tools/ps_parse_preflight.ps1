function Test-PSSyntax {
  param([Parameter(Mandatory=$true)][string]$Path)
  $src = Get-Content -LiteralPath $Path -Raw
  $errs = $null
  $tokens = $null
  $ast = [System.Management.Automation.Language.Parser]::ParseInput($src, [ref]$tokens, [ref]$errs)
  if ($errs -and $errs.Count -gt 0) {
    $errs | ForEach-Object {
      "{0}:{1}:{2} {3}" -f $_.Extent.File, $_.Extent.StartLineNumber, $_.Extent.StartColumnNumber, $_.Message
    } | Write-Output
    exit 2
  } else {
    "OK" | Write-Output
    exit 0
  }
}
