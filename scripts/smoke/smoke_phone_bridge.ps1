$h = Invoke-WebRequest http://127.0.0.1:5080/health -UseBasicParsing | Select-Object -Expand StatusCode
if ($h -ne 200) { Write-Error "health failed"; exit 2 }
Invoke-WebRequest http://127.0.0.1:5080/queue -Method POST -ContentType "application/json" -Body (@{ cmd="restart:heartbeat" } | ConvertTo-Json) | Out-Null
Invoke-WebRequest http://127.0.0.1:5080/plan/select -Method POST -ContentType "application/json" -Body (@{ id="13D" } | ConvertTo-Json) | Out-Null
Write-Output "[OK] phone bridge basic smoke passed"
