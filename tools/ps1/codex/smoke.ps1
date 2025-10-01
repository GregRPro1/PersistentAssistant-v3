Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$RepoRoot = Get-Location
$tmp = Join-Path $RepoRoot "tmp\logs"
if (-not (Test-Path $tmp)) { New-Item -ItemType Directory -Force $tmp | Out-Null }
$log = Join-Path $tmp ("pytest_smoke_{0}.txt" -f (Get-Date -Format "yyyyMMdd_HHmmss"))
$venvPy = Join-Path $RepoRoot ".venv\Scripts\python.exe"
$py = if (Test-Path $venvPy) { $venvPy } else { "python" }
Write-Host "== Running: pytest -q -m smoke =="
$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName = $py
$psi.Arguments = "-m pytest -q -m smoke"
$psi.WorkingDirectory = $RepoRoot
$psi.UseShellExecute = $false
$psi.RedirectStandardOutput = $true
$psi.RedirectStandardError  = $true
$p = New-Object System.Diagnostics.Process
$p.StartInfo = $psi
[void]$p.Start()
$out = $p.StandardOutput.ReadToEnd()
$err = $p.StandardError.ReadToEnd()
$p.WaitForExit()
$out | Set-Content -Encoding UTF8 -Path $log
if ($err) { Add-Content -Encoding UTF8 -Path $log -Value "`n---- STDERR ----`n$err" }
Write-Host "---- PyTest (tail) ----"
Get-Content $log -Tail 60
Write-Host "-----------------------"
exit $p.ExitCode
