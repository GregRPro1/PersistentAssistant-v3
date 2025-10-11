# Generate stubs (idempotent) and run P3 smokes in parallel
pwsh .\pal\scripts\ps\gen_smoke_for_phase.ps1 -Phase P3 | Out-Null
pwsh .\pal\scripts\ps\run_smoke_phase.ps1 -Phase P3
