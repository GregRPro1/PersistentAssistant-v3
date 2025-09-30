$ErrorActionPreference='Stop'

function Find-RepoRoot([string]$start) {
  if (-not $start) { $start = $PSScriptRoot }
  $cur = Resolve-Path -LiteralPath $start
  for ($i=0; $i -lt 12; $i++) {
    if (Test-Path (Join-Path $cur '.git')) { return $cur }
    $parent = Split-Path -Parent $cur
    if ($parent -eq $cur) { break }
    $cur = $parent
  }
  return (Get-Location).Path
}

$root = Find-RepoRoot $PSScriptRoot
$ops = Join-Path $root 'reports\ops'
New-Item -ItemType Directory -Force -Path $ops | Out-Null

$stamp = (Get-Date).ToString('yyyyMMdd_HHmmss')
$marker = Join-Path $ops 'hello_e2e_mobile.txt'
"HELLO E2E via mobile apply @ $stamp" | Out-File -FilePath $marker -Encoding utf8

Write-Host "Wrote marker: $marker"

# Optional: commit on a short branch (safe if Git present)
try {
  Push-Location $root
  git checkout -B step/PA-350-hello-e2e | Out-Null
  git add $marker
  git commit -m "PA-350: hello e2e marker @ $stamp" | Out-Null
  git push -u origin step/PA-350-hello-e2e | Out-Null
  Pop-Location
  Write-Host "Committed and pushed branch step/PA-350-hello-e2e"
} catch {
  Write-Host "Git commit/push skipped: $($_.Exception.Message)"
}

# Exit success
exit 0
