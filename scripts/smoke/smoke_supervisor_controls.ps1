$ErrorActionPreference="Stop"
$base = "http://127.0.0.1:6060"
$deadline = (Get-Date).AddSeconds(20)
$up = $false
while((Get-Date) -lt $deadline) {
  try { $code = (Invoke-WebRequest ($base + "/health") -UseBasicParsing | Select-Object -Expand StatusCode); if ($code -eq 200) { $up = $true; break } } catch { Start-Sleep -Milliseconds 250 }
}
if (-not $up) { throw "supervisor /health not reachable" }
Invoke-WebRequest "$base/control?service=phonesvc&action=restart"  -Method POST | Out-Null
Invoke-WebRequest "$base/control?service=tunnelsvc&action=restart" -Method POST | Out-Null
$st = Invoke-WebRequest "$base/status" -UseBasicParsing | Select-Object -Expand Content | ConvertFrom-Json
if (-not $st.services.phonesvc)  { throw "phonesvc not present in status" }
if (-not $st.services.tunnelsvc) { throw "tunnelsvc not present in status" }
"OK: supervisor controls for phone + tunnel available"
