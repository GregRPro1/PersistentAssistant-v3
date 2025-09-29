$ErrorActionPreference='Stop'
# Pick python
$py = Join-Path $PSScriptRoot '..\..\..\.venv\Scripts\python.exe'
if (-not (Test-Path $py)) { $py = 'python' }
# Check missing modules via -c string (works on Windows)
$code = & $py -c 'import importlib,sys;mods=("msal","requests","pyyaml");m=[x for x in mods if __import__("importlib").util.find_spec(x) is None];print(";".join(m))'
if ($LASTEXITCODE -ne 0) { throw "python probe failed" }
$missing = @()
if ($code) { $missing = $code -split ';' | ? { $_ } }
if ($missing.Count -gt 0) {
  Write-Host ("Installing: {0}" -f ($missing -join ', '))
  & $py -m pip install --upgrade $missing
  if ($LASTEXITCODE -ne 0) { throw "pip install failed" }
} else {
  Write-Host "All deps present."
}
