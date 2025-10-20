$ErrorActionPreference="Stop"
$base = "http://127.0.0.1:6060"
$deadline = (Get-Date).AddSeconds(20)
$up = $false
while((Get-Date) -lt $deadline) {
  try { $code = (Invoke-WebRequest ($base + "/health") -UseBasicParsing | Select-Object -Expand StatusCode); if ($code -eq 200) { $up = $true; break } } catch { Start-Sleep -Milliseconds 250 }
}
if (-not $up) { throw "supervisor /health not reachable" }
Start-Sleep -Seconds 2
$code2 = (Invoke-WebRequest ($base + "/status") -UseBasicParsing | Select-Object -Expand StatusCode)
if ($code2 -ne 200) { throw "/status not 200 after startup" }
"OK: supervisor stayed up and answered /status"
