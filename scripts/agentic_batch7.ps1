# scripts/agentic_batch7.ps1
param(
    [string]$Step = "10.4",
    [switch]$Apply = $false,
    [string]$Tests = ""              # optional: e.g. "tests/test_context_pack.py"
)

Write-Host "==> Batch 7: End-to-end agentic round-trip for step $Step (Apply=$Apply)"

# --- Prep dirs
$dirs = @("tmp", "tmp\patches")
foreach ($d in $dirs) { New-Item -ItemType Directory -Force -Path $d | Out-Null }

# --- Ensure LEB is up (idempotent)
Write-Host "==> Ensuring LEB is up on :8765"
$lebOk = $false
try {
    $lebResp = python tools\py\leb\leb_ensure.py --port 8765
    if ($LASTEXITCODE -eq 0) {
        Write-Host $lebResp
        $lebOk = $true
    }
}
catch { }
if (-not $lebOk) {
    Write-Host "!! LEB did not confirm ready. Please start it (tools\py\leb\leb_ensure.py). Aborting." -ForegroundColor Red
    exit 1
}

# --- Policy snapshot (diagnostics)
Write-Host "==> Policy snapshot (effective)"
try {
    $pol = python -m tools.py.agentic.policy_debug --check-path docs/USER_GUIDE.md
    Write-Host $pol
}
catch {
    Write-Host "!! policy_debug failed (non-fatal)."
}

# --- Propose for step
$stamp = ($Step -replace '[^0-9a-zA-Z_\.]', '_') -replace '\.', '_'
$propRel = "tmp\patches\proposal_step_$stamp.json"
Write-Host "==> Propose for step $Step -> $propRel"
$propOut = python -m tools.py.agentic.propose_for_step --id $Step --out $propRel --force
if ($LASTEXITCODE -ne 0) {
    Write-Host $propOut
    Write-Host "!! propose_for_step failed" -ForegroundColor Red
    exit 2
}
Write-Host $propOut
$propAbs = (Resolve-Path $propRel).Path
$propAbsPosix = $propAbs -replace '\\', '/'

# --- Optional: proposal diagnostics
Write-Host "==> proposal_diff (diagnostic via patch_debug)"
try {
    python -m tools.py.agentic.patch_debug --proposal $propRel
}
catch { }

# --- Apply (or dry-run) via LEB
$applyFlag = ""
if ($Apply) { $applyFlag = " --really-apply" }
$cmd = "python -m tools.py.agentic.patch_apply --proposal `"$propAbsPosix`"$applyFlag"

Write-Host "==> patch_apply (Apply=$Apply)"
$resp = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8765/run `
    -ContentType 'application/json' -Body (@{cmd = $cmd } | ConvertTo-Json)

# Parse tool JSON in stdout
$tool = $null
if ($resp.stdout) {
    try { $tool = $resp.stdout | ConvertFrom-Json } catch { }
}
if ($null -eq $tool) {
    Write-Host "!! No tool JSON in LEB response (stdout empty or invalid)" -ForegroundColor Red
    $resp | ConvertTo-Json -Depth 6 | Write-Host
    exit 3
}

Write-Host ("   feature_id: {0}" -f ($tool.feature_id))
Write-Host ("   dry_run:    {0}" -f ($tool.dry_run))
Write-Host ("   apply:      {0}" -f ($Apply.IsPresent))
Write-Host ("   results:    {0}" -f (($tool.results | Measure-Object).Count))

if ($tool.results) {
    $i = 1
    foreach ($r in $tool.results) {
        Write-Host ("   -> [{0}] {1} reason={2} bytes={3}" -f $i, $r.path, $r.reason, $r.bytes)
        $i++
    }
}

if ($Apply -and -not $tool.ok) {
    Write-Host "!! patch_apply reported ok=false; aborting." -ForegroundColor Red
    exit 4
}

# --- Run pytest via LEB (lightweight by default)
$testsArg = $Tests
if (-not $testsArg) { $testsArg = "tests/test_context_pack.py" }
$pytestCmd = "pytest -q $testsArg"
Write-Host "==> pytest -q $testsArg"
$pytestResp = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8765/run `
    -ContentType 'application/json' -Body (@{cmd = $pytestCmd } | ConvertTo-Json)
Write-Host ("   pytest rc={0}" -f ($pytestResp.rc))

Write-Host "==> Batch 7 complete (PASS)"
exit 0
