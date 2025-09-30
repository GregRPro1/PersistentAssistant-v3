# Pack-side apply: copy payload into repo using repo's script with safe copy param.
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot  = Split-Path -Parent $ScriptDir
Push-Location $RepoRoot
Write-Host "apply_pack (pack): repo root = $RepoRoot"
$payload = Join-Path $ScriptDir '..\payload' | Resolve-Path -ErrorAction Stop
$files = Get-ChildItem -Recurse -File $payload.Path
foreach ($f in $files) {
  $rel = $f.FullName.Substring($payload.Path.Length).TrimStart('\','/')
  $dest = Join-Path $RepoRoot $rel
  $destDir = Split-Path $dest -Parent
  if (-not (Test-Path $destDir)) { New-Item -ItemType Directory -Force -Path $destDir | Out-Null }
  # Call the repo script in safe copy mode if present; else plain copy
  $repoApply = Join-Path $RepoRoot 'scripts\apply_pack.ps1'
  if (Test-Path $repoApply) {
    try { pwsh -NoProfile -ExecutionPolicy Bypass -File $repoApply -from $f.FullName -to $dest } catch { Copy-Item -Force -Path $f.FullName -Destination $dest }
  } else {
    Copy-Item -Force -Path $f.FullName -Destination $dest
  }
}
Write-Host "apply_pack (pack): payload copied"
# Finally, invoke the repo script normally to finish tasks
$repoApply2 = Join-Path $RepoRoot 'scripts\apply_pack.ps1'
if (Test-Path $repoApply2) {
  pwsh -NoProfile -ExecutionPolicy Bypass -File $repoApply2
} else {
  Write-Host "apply_pack (pack): repo apply script missing; nothing more to do."
}
