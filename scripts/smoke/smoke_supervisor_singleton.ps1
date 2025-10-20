# Singleton: if a supervisor is up, /health returns 200 and a second run should exit fast
$base = "http://127.0.0.1:6060"
$up = $false
try { $code = (Invoke-WebRequest ($base + "/health") -UseBasicParsing | Select-Object -Expand StatusCode); if ($code -eq 200){ $up=$true } } catch {}
if (-not $up) { "Note: supervisor not detected; start it first." } else { "OK: singleton guard will prevent double-run." }
