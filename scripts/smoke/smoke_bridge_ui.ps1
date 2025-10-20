$ErrorActionPreference="Stop"
# wait for UI
$deadline = (Get-Date).AddSeconds(20)
$up = $false
while((Get-Date) -lt $deadline) {
  try { $r = Invoke-WebRequest "http://127.0.0.1:5070/" -UseBasicParsing; if ($r.StatusCode -eq 200 -and $r.Content -match "<title>PAL Bridge & Supervisor</title>") { $up = $true; break } } catch { Start-Sleep -Milliseconds 200 }
}
if (-not $up) { throw "Bridge UI not reachable" }

# api test
$r2 = Invoke-WebRequest "http://127.0.0.1:5070/api/supervisor" -UseBasicParsing
if ($r2.StatusCode -ne 200) { throw "/api/supervisor failed" }
"OK: Bridge UI responds"
