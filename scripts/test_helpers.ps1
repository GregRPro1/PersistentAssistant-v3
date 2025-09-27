param(
  [string]tests/test_proposal_api.py,
  [switch]
)

function Invoke-PyTests {
  param(
    [Parameter(Mandatory=True)][string]tests/test_proposal_api.py,
    [switch]  # use -V instead of -Verbose to avoid the common-parameter clash
  )
  # Compose pytest args
   = if () { "-vv" } else { "-q" }

  # Run pytest
  & pytest  tests/test_proposal_api.py
   = 0

  # Clear, explicit summary
  if ( -eq 0) {
    Write-Host "✅ PASS: tests/test_proposal_api.py" -ForegroundColor Green
  } else {
    Write-Host "❌ FAIL: tests/test_proposal_api.py (exit )" -ForegroundColor Red
  }

  return 
}

# If invoked as a script with -Run, execute immediately
if ( -and tests/test_proposal_api.py) {
  exit (Invoke-PyTests -Path tests/test_proposal_api.py)
}
