param([string]$TaskName = 'PA_PackFetcher', [int]$EveryMinutes = 1)
$ErrorActionPreference='Stop'

function Quote([string]$s) {
  if ($s -match '\s') { return '"' + $s + '"' } else { return $s }
}

function PwshPath() {
  $candidates = @(
    "$env:ProgramFiles\PowerShell\7\pwsh.exe",
    "$env:ProgramFiles\PowerShell\7-preview\pwsh.exe",
    "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe"
  )
  foreach ($p in $candidates) { if (Test-Path $p) { return $p } }
  return "powershell.exe"
}

$root = (Resolve-Path (Split-Path -Parent $MyInvocation.MyCommand.Path)).Path
$script = Join-Path $root 'run_pack_fetcher.ps1'
$pwsh = PwshPath()

$tr = (Quote($pwsh) + ' -NoProfile -ExecutionPolicy Bypass -File ' + Quote($script))
$cmd = @('SCHTASKS','/CREATE','/SC','MINUTE','/MO',"$EveryMinutes",'/TN',"$TaskName",'/TR',"$tr",'/RL','HIGHEST','/F')

$p = Start-Process -FilePath $cmd[0] -ArgumentList $cmd[1..($cmd.Length-1)] -Wait -PassThru -WindowStyle Hidden
if ($p.ExitCode -ne 0) {
  Write-Error "schtasks failed with exit code $($p.ExitCode). Try running as Administrator or use Task Scheduler UI."
} else {
  Write-Host "Scheduled task '$TaskName' created to run every $EveryMinutes minute(s)."
}