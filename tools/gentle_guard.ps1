param(
  [string]$Root = ".",
  [string]$PatternsFile = "tools\guard_patterns.txt",
  [string]$OutJson = "tmp\logs\guard_report.json"
)

function Read-Patterns {
  param([string]$Path)
  if (!(Test-Path $Path)) { return @() }
  $lines = Get-Content -Raw -ErrorAction SilentlyContinue $Path | Out-String
  $col = @()
  foreach ($ln in ($lines -split "`r?`n")) {
    $s = $ln.Trim()
    if ($s.Length -eq 0) { continue }
    if ($s.StartsWith("#")) { continue }
    $col += $s
  }
  return $col
}

$patterns = Read-Patterns -Path $PatternsFile
$violations = @()

# Scan a reasonable set of files
$targets = Get-ChildItem -Path $Root -Recurse -File -ErrorAction SilentlyContinue |
  Where-Object {
    $_.FullName -notmatch "\\\.venv\\|\\node_modules\\|\\\.git\\|\\tmp\\archive\\"
  } |
  Where-Object {
    $_.Extension -in @(".ps1",".py",".yaml",".yml",".md",".txt",".psm1",".psd1")
  }

foreach ($f in $targets) {
  $text = ""
  try { $text = Get-Content -Raw -LiteralPath $f.FullName -ErrorAction Stop }
  catch { continue }
  foreach ($pat in $patterns) {
    try {
      $m = [regex]::Match($text, $pat, [System.Text.RegularExpressions.RegexOptions]::Multiline)
      if ($m.Success) {
        $sample = $m.Value
        $violations += [pscustomobject]@{
          file     = $f.FullName
          pattern  = $pat
          sample   = $sample
        }
      }
    } catch {
      # bad regex? skip
      continue
    }
  }
}

# Write JSON safely
$dir = Split-Path -Parent $OutJson
if (!(Test-Path $dir)) { New-Item -ItemType Directory -Path $dir | Out-Null }
$violations | ConvertTo-Json -Depth 4 | Set-Content -Path $OutJson -Encoding UTF8

# Summary
if ($violations.Count -gt 0) {
  Write-Host "[FORBIDDEN GUARD] VIOLATIONS FOUND:" -ForegroundColor Yellow
  foreach ($v in $violations) {
    $short = $v.sample
    if ($short.Length -gt 40) { $short = $short.Substring(0,40) }
    Write-Host " - $($v.file)  :: $($v.pattern)  :: '$short'"
  }
  Write-Host ("Total violations: {0}" -f $violations.Count)
  exit 2   # non-zero to mark presence of violations
} else {
  Write-Host "[FORBIDDEN GUARD] No violations found."
  exit 0
}
