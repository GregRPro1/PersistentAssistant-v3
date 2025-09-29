# Creates a Startup shortcut that runs the pack fetcher loop at user logon (no admin required).
$ErrorActionPreference='Stop'

function PwshPath {
  $candidates = @(
    "$env:ProgramFiles\PowerShell\7\pwsh.exe",
    "$env:ProgramFiles\PowerShell\7-preview\pwsh.exe",
    "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe"
  )
  foreach ($p in $candidates) { if (Test-Path $p) { return $p } }
  return "powershell.exe"
}

function Find-RepoRoot([string]$start) {
  if (-not $start) { $start = $PSScriptRoot }
  $cur = Resolve-Path -LiteralPath $start
  for ($i=0; $i -lt 10; $i++) {
    if (Test-Path (Join-Path $cur '.git')) { return $cur }
    $parent = Split-Path -Parent $cur
    if ($parent -eq $cur) { break }
    $cur = $parent
  }
  return (Get-Location).Path
}

$root = Find-RepoRoot $null
$script = Join-Path $root 'tools\ps1\run_pack_fetcher.ps1'
$pwsh = PwshPath

$startup = Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs\Startup'
$lnk = Join-Path $startup 'PA_PackFetcher.lnk'

$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut($lnk)
$Shortcut.TargetPath = $pwsh
$Shortcut.Arguments  = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$script`""
$Shortcut.WorkingDirectory = (Split-Path -Parent $script)
$Shortcut.WindowStyle = 7  # Minimized
$Shortcut.IconLocation = "$pwsh,0"
$Shortcut.Save()

Write-Host "Startup shortcut created: $lnk"
Write-Host "It will start the fetcher loop at user logon (no admin privileges needed)."