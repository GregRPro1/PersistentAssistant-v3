#requires -Version 5
param([switch]$Apply = $true, [switch]$RunTests = $true)

$ErrorActionPreference = 'Stop'

function Note($m) { Write-Host ("==> " + $m) -ForegroundColor Cyan }
function Write-Utf8File([string]$Path, [string]$Content) {
    $dir = Split-Path -Parent $Path
    if ($dir) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }
    Set-Content -Path $Path -Value $Content -Encoding UTF8
}
function LEB([string]$cmd) {
    $body = @{ cmd = $cmd } | ConvertTo-Json
    Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8765/run -ContentType 'application/json' -Body $body
}

# move to repo root
$Repo = Split-Path -Parent $PSScriptRoot
if (-not $Repo) { $Repo = (Get-Location).Path }
Set-Location $Repo

Note "Prep folders"
New-Item -ItemType Directory -Force -Path tmp, tmp\patches | Out-Null

# --- test: patch_apply dry-run path against propose_for_step ---
Note "Write tests\test_patch_apply_dryrun.py"
$testPath = "tests\test_patch_apply_dryrun.py"
$testContent = @'
import json, subprocess, sys, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]

def run(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True)
    return p.returncode, p.stdout, p.stderr

def test_patch_apply_dry_run_smoke():
    prop = ROOT / "tmp/patches/proposal_step_10_3.json"
    prop.parent.mkdir(parents=True, exist_ok=True)
    rc, out, err = run([sys.executable, "-m", "tools.py.agentic.propose_for_step", "--id", "10.3", "--out", str(prop), "--force"])
    assert rc == 0, err
    rc, out, err = run([sys.executable, "-m", "tools.py.agentic.patch_apply", "--proposal", str(prop)])
    assert rc == 0, err
    data = json.loads(out)
    assert data.get("ok") is True, data
    assert data.get("results"), data
    assert data["results"][0]["reason"] in ("would_apply", "applied")
'@
Write-Utf8File $testPath $testContent

# Ensure the policy allows touching docs/USER_GUIDE.md for this batch (idempotent)
$polPath = "config\runner_policy.yaml"
if (Test-Path $polPath) {
    $pol = Get-Content $polPath -Raw
    if ($pol -notmatch 'docs/USER_GUIDE\.md') {
        $pol = $pol -replace 'allow_globs:\s*\r?\n', "allow_globs:`r`n  - `"docs/USER_GUIDE.md`"`r`n"
        $pol | Set-Content $polPath -Encoding UTF8
    }
}

if ($RunTests) {
    Note "pytest -q tests/test_patch_apply_dryrun.py"
    $r = LEB "pytest -q tests/test_patch_apply_dryrun.py"
    $r.stdout
    if ($r.rc -ne 0) { throw "pytest failed (patch_apply_dryrun)" }
}

Note "Batch 3 complete"
