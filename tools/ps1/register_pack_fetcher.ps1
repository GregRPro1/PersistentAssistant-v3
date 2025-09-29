param([string]$TaskName = 'PA_PackFetcher', [int]$EveryMinutes = 1)
$ErrorActionPreference='Stop'

function Quote([string]$s) {
  if ($s -match '\s') { return '"' + $s + '"' } else { return $s }
}

function PwshPath {
  $candidates = @(
    "$env:ProgramFiles\PowerShell\7\pwsh.exe",
    "$env:ProgramFiles\PowerShell\7-preview\pwsh.exe",
    "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe"
  )
  foreach ($p in $candidates) { if (Test-Path $p) { return $p } }
  return "powershell.exe"
}

# repo root = parent of this script folder
$root = (Resolve-Path (Split-Path -Parent $MyInvocation.MyCommand.Path)).Path
$script = Join-Path $root 'run_pack_fetcher.ps1'
$pwsh = (PwshPath)

$tr = (Quote($pwsh) + ' -NoProfile -ExecutionPolicy Bypass -File ' + Quote($script))

$args = @(
  '/CREATE',
  '/SC','MINUTE','/MO',"$EveryMinutes",
  '/TN',"$TaskName",
  '/TR',"$tr",
  '/RL','HIGHEST',
  '/F'
)

# Use Start-Process for reliable quoting
$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName = 'SCHTASKS'
$psi.Arguments = ($args -join ' ')
$psi.UseShellExecute = $false
$psi.RedirectStandardOutput = $true
$psi.RedirectStandardError  = $true

$p = New-Object System.Diagnostics.Process
$p.StartInfo = $psi
$null = $p.Start()
$stdout = $p.StandardOutput.ReadToEnd()
$stderr = $p.StandardError.ReadToEnd()
$p.WaitForExit()

if ($p.ExitCode -ne 0) {
  Write-Error "schtasks failed ($($p.ExitCode)). Stdout:`n$stdout`nStderr:`n$stderr`nTry running as Administrator or use Task Scheduler UI."
} else {
  Write-Host $stdout.TrimEnd()
  Write-Host "Scheduled task '$TaskName' created to run every $EveryMinutes minute(s)."
}