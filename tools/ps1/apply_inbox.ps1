param(
  [string]$Inbox = "_inbox",
  [string]$Processed = "_inbox\processed"
)
$ErrorActionPreference='Stop'

function Find-RepoRoot([string]$start) {
  if (-not $start) { $start = (Split-Path -Parent $MyInvocation.MyCommand.Path) }
  $cur = Resolve-Path -LiteralPath $start
  for ($i=0; $i -lt 10; $i++) {
    if (Test-Path (Join-Path $cur '.git')) { return $cur }
    $parent = Split-Path -Parent $cur
    if ($parent -eq $cur) { break }
    $cur = $parent
  }
  return (Get-Location).Path
}

$root = Find-RepoRoot $PSScriptRoot
$inboxPath = Join-Path $root $Inbox
$procPath  = Join-Path $root $Processed

New-Item -ItemType Directory -Force -Path $inboxPath | Out-Null
New-Item -ItemType Directory -Force -Path $procPath  | Out-Null

$zips = Get-ChildItem -Path $inboxPath -Filter *.zip -File | Sort-Object LastWriteTime
if (-not $zips) { Write-Host "apply_inbox: no zips in $inboxPath"; exit 0 }

foreach ($zip in $zips) {
  $stamp = Get-Date -Format "yyyyMMdd_HHmmss"
  $stage = Join-Path $root ("_staging_{0}" -f $stamp)
  New-Item -ItemType Directory -Force -Path $stage | Out-Null

  Write-Host "apply_inbox: expanding $($zip.Name) to $stage"
  Expand-Archive -LiteralPath $zip.FullName -DestinationPath $stage -Force

  $apply = Join-Path $stage "scripts\apply_pack.ps1"
  if (Test-Path $apply) {
    Write-Host "apply_inbox: applying $($zip.Name)"
    & pwsh -NoProfile -ExecutionPolicy Bypass -File $apply
    $code = $LASTEXITCODE
    Write-Host "apply_inbox: apply exit $code"
  } else {
    Write-Warning "apply_inbox: scripts\apply_pack.ps1 not found in $($zip.Name)"
    $code = 1
  }

  $dest = Join-Path $procPath $zip.Name
  $i=1
  while (Test-Path $dest) {
    $dest = Join-Path $procPath ("{0}_{1}{2}" -f $zip.BaseName,$i,$zip.Extension); $i++
  }
  Move-Item -LiteralPath $zip.FullName -Destination $dest
  Write-Host "apply_inbox: moved $($zip.Name) -> $dest"

  if ($code -ne 0) { Write-Warning "apply_inbox: non-zero exit ($code) for $($zip.Name)" }
}
exit 0