param(
  [string[]]$Files,
  [switch]$AddAST,
  [switch]$AddLogs,
  [string]$OutDir = "tmp\logs",
  [string]$Name = "support_bundle"
)

$python = Join-Path ".venv\Scripts" "python.exe"
if (-not (Test-Path $python)) { $python = "python" }

$cmd = @($python, "tools/py/pack/make_support_bundle.py", "--outdir", $OutDir, "--name", $Name)
if ($AddAST)  { $cmd += "--gen-ast" }
if ($AddLogs) { $cmd += "--add-logs" }

foreach ($f in ($Files | Where-Object { $_ -and $_.Trim() -ne "" })) {
  $cmd += @("--include", $f)
}

Write-Host "Running: $($cmd -join ' ')"
$p = Start-Process -NoNewWindow -FilePath $cmd[0] -ArgumentList $cmd[1..($cmd.Count-1)] -PassThru -Wait
if ($p.ExitCode -ne 0) {
  Write-Error "make_support_bundle failed (exit $($p.ExitCode))"
}
