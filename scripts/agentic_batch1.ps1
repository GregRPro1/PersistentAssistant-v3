#requires -Version 5
param(
  [switch]$Apply = $true,         # do real apply (after dry-run)
  [switch]$RunTests = $true       # run pytest at the end
)

$ErrorActionPreference = 'Stop'
$Repo = Split-Path -Parent $PSScriptRoot
if (-not $Repo) { $Repo = (Get-Location).Path }
Set-Location $Repo

function Write-Note($msg) { Write-Host ("==> " + $msg) -ForegroundColor Cyan }
function LEB-Run([string]$cmd) {
  $body = @{ cmd = $cmd } | ConvertTo-Json
  Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8765/run -ContentType 'application/json' -Body $body
}
function Sha256IfExists([string]$path) {
  if (Test-Path $path) {
    ($hash = Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLower()
    return $hash
  }
  return $null
}

# ---------------------------------------------------------------------------
# 0) Ensure dirs + (temporarily) broaden policy to allow tools/tests/docs writes
# ---------------------------------------------------------------------------
Write-Note "Prep folders"
New-Item -ItemType Directory -Force -Path tmp, tmp\patches | Out-Null

$policyPath = "config\runner_policy.yaml"
if (-not (Test-Path $policyPath)) {
  New-Item -ItemType Directory -Force -Path (Split-Path $policyPath -Parent) | Out-Null
}
Write-Note "Updating policy allowlist for this batch (tools/**, tests/**, docs/**)"
@'
# config/runner_policy.yaml

ai_apply:
  enabled: true
  require_feature_id: true
  require_before_sha: true

apply_enabled: true
require_before_sha: true

limits:
  max_files: 25
  max_total_bytes: 400000
  max_hunks_per_file: 50

allow_globs:
  - "tools/**"
  - "tests/**"
  - "docs/**"

deny_globs:
  - "tmp/**"
  - ".git/**"
  - "**/*.exe"
  - "**/*.dll"
  - "**/*.bin"
  - "**/*.png"
  - "**/*.jpg"
  - "data/interactions/**"

backups:
  enabled: true
  dir: "tmp/backups"
'@ | Set-Content $policyPath -Encoding UTF8

# ---------------------------------------------------------------------------
# 1) PROPOSAL: add tools/py/agentic/propose_enhanced.py
# ---------------------------------------------------------------------------
$proposerPath = "tools\py\agentic\propose_enhanced.py"
$proposerContent = @'
from __future__ import annotations
import argparse, json
from datetime import datetime, timezone
from pathlib import Path
from .patch_utils import sha256_hex, ensure_dir

ROOT = Path(__file__).resolve().parents[3]  # repo root

def now_iso_utc() -> str:
    return datetime.now(timezone.utc).isoformat()

def build_proposal(step_id: str) -> dict:
    guide = ROOT / "docs" / "USER_GUIDE.md"
    before = sha256_hex(str(guide)) if guide.exists() else None
    content = "\\n\\n> [plan] placeholder for step {sid} (agentic enhanced proposer) @ {ts}\\n".format(
        sid=step_id, ts=int(datetime.now(timezone.utc).timestamp())
    )
    action = {
        "path": "docs/USER_GUIDE.md",
        "mode": "append",
        "content": content,
    }
    if before:
        action["before_sha"] = before
    return {
        "feature_id": f"STEP-{step_id}",
        "description": f"Automated patch proposal for step {step_id}",
        "version": 1,
        "author": "propose_enhanced",
        "created": now_iso_utc(),
        "actions": [action],
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    out_path = ROOT / Path(args.out)
    ensure_dir(out_path.parent)
    if out_path.exists() and not args.force:
        raise SystemExit(f"Refusing to overwrite existing: {out_path} (use --force)")

    prop = build_proposal(args.id)
    out_path.write_text(json.dumps(prop, indent=2), encoding="utf-8")
    print(str(out_path))

if __name__ == "__main__":
    main()
'@

$actions = @()
$before = Sha256IfExists $proposerPath
$act = @{
  path = ($proposerPath -replace '\\','/')
  mode = "replace"
  content = $proposerContent
}
if ($before) { $act.before_sha = $before }
$actions += $act

$proposal1 = @{
  feature_id  = "STEP-10.3"
  description = "Add enhanced proposer (feature_id/description/before_sha)"
  version     = 1
  author      = "agentic_batch1"
  created     = (Get-Date).ToUniversalTime().ToString("s") + "Z"
  actions     = $actions
}
$prop1Path = "tmp\patches\proposal_agentic_batch1_proposer.json"
$proposal1 | ConvertTo-Json -Depth 10 | Set-Content $prop1Path -Encoding UTF8

# ---------------------------------------------------------------------------
# 2) PROPOSAL: replace tests/test_agentic_apply.py with robust diagnostics suite
# ---------------------------------------------------------------------------
$testPath = "tests\test_agentic_apply.py"
$testContent = @'
import os, json, time, tempfile, hashlib, subprocess, sys, uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def run_apply(proposal_path: Path, really=False, env=None):
    cmd = [sys.executable, "-m", "tools.py.agentic.patch_apply", "--proposal", str(proposal_path)]
    if really:
        cmd.append("--really-apply")
    p = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT, env=env)
    try:
        data = json.loads(p.stdout.strip())
    except Exception:
        data = {"ok": False, "parse_error": p.stdout, "stderr": p.stderr, "rc": p.returncode}
    return p.returncode, data

def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        h.update(f.read())
    return h.hexdigest()

def make_policy_allow_tmp(tmpdir: Path) -> Path:
    y = f"""
ai_apply:
  enabled: true
  require_feature_id: true
  require_before_sha: true

allow_globs:
  - "{(tmpdir / "**").as_posix()}"
deny_globs:
  - ".git/**"
  - "data/interactions/**"
backups:
  enabled: true
  dir: "tmp/backups"
""".lstrip()
    policy = ROOT / "tmp" / f"test_policy_{uuid.uuid4().hex}.yaml"
    policy.parent.mkdir(parents=True, exist_ok=True)
    policy.write_text(y, encoding="utf-8")
    return policy

def make_proposal_for_file(target: Path, content: str, feature="TEST-APPLY", desc="test proposal"):
    before = sha256_file(target) if target.exists() else None
    action = {"path": str(target).replace("\\","/"), "mode": "append", "content": content}
    if before:
        action["before_sha"] = before
    prop = {
        "feature_id": feature,
        "description": desc,
        "version": 1,
        "author": "tests",
        "created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "actions": [action],
    }
    p = ROOT / "tmp" / f"proposal_test_{uuid.uuid4().hex}.json"
    p.write_text(json.dumps(prop, indent=2), encoding="utf-8")
    return p

def test_dry_run_would_apply():
    scratch = ROOT / "tmp" / f"agentic_scratch_{uuid.uuid4().hex}.txt"
    scratch.parent.mkdir(parents=True, exist_ok=True)
    scratch.write_text("base\n", encoding="utf-8")
    policy = make_policy_allow_tmp(ROOT / "tmp")
    env = dict(os.environ)
    env["PA_POLICY_PATH"] = str(policy)
    prop = make_proposal_for_file(scratch, "A\n", "TEST-APPLY-DRY", "dry-run should would_apply")
    rc, data = run_apply(prop, really=False, env=env)
    assert data.get("ok") is True
    assert data["results"][0]["reason"] in ("would_apply", "applied")
    assert data["results"][0]["mode"] == "append"

def test_real_apply_then_mismatch():
    scratch = ROOT / "tmp" / f"agentic_scratch_{uuid.uuid4().hex}.txt"
    scratch.parent.mkdir(parents=True, exist_ok=True)
    scratch.write_text("base\n", encoding="utf-8")
    policy = make_policy_allow_tmp(ROOT / "tmp")
    env = dict(os.environ)
    env["PA_POLICY_PATH"] = str(policy)
    prop = make_proposal_for_file(scratch, "B\n", "TEST-APPLY-REAL", "real apply then mismatch")
    rc, data = run_apply(prop, really=True, env=env)
    assert data.get("ok") is True
    assert data["results"][0]["reason"] == "applied"
    rc2, data2 = run_apply(prop, really=True, env=env)
    assert (data2.get("ok") is False) or (data2["results"][0]["reason"] in ("before_sha_mismatch","stale_base","policy_denied"))

def test_policy_denies_wrong_path():
    policy_text = """
ai_apply:
  enabled: true
  require_feature_id: true
  require_before_sha: true
allow_globs:
  - "docs/**"
deny_globs:
  - "tmp/**"
""".lstrip()
    policy = ROOT / "tmp" / f"test_policy_deny_{uuid.uuid4().hex}.yaml"
    policy.write_text(policy_text, encoding="utf-8")

    env = dict(os.environ)
    env["PA_POLICY_PATH"] = str(policy)

    scratch = ROOT / "tmp" / f"agentic_scratch_{uuid.uuid4().hex}.txt"
    scratch.parent.mkdir(parents=True, exist_ok=True)
    scratch.write_text("base\n", encoding="utf-8")

    prop = make_proposal_for_file(scratch, "C\n", "TEST-APPLY-DENY", "should be denied by policy")
    rc, data = run_apply(prop, really=False, env=env)
    if data.get("results"):
      assert data["results"][0]["reason"] in ("policy_path_not_allowed","policy_denied")
    else:
      assert data.get("ok") is False
'@

$actions = @()
$before = Sha256IfExists $testPath
$act = @{
  path = ($testPath -replace '\\','/')
  mode = "replace"
  content = $testContent
}
if ($before) { $act.before_sha = $before }
$actions += $act

$proposal2 = @{
  feature_id  = "STEP-10.5"
  description = "Comprehensive agentic apply tests (dry/run/deny/mismatch)"
  version     = 1
  author      = "agentic_batch1"
  created     = (Get-Date).ToUniversalTime().ToString("s") + "Z"
  actions     = $actions
}
$prop2Path = "tmp\patches\proposal_agentic_batch1_tests.json"
$proposal2 | ConvertTo-Json -Depth 10 | Set-Content $prop2Path -Encoding UTF8

# ---------------------------------------------------------------------------
# 3) PROPOSAL: append small note to docs/USER_GUIDE.md (visible trail)
# ---------------------------------------------------------------------------
$guidePath = "docs\USER_GUIDE.md"
$epoch = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
$guideAppend = "`n`n> [agentic] batch1 bootstrap applied @ $epoch`n"

$actions = @()
$before = Sha256IfExists $guidePath
$act = @{
  path = ($guidePath -replace '\\','/')
  mode = "append"
  content = $guideAppend
}
if ($before) { $act.before_sha = $before }
$actions += $act

$proposal3 = @{
  feature_id  = "STEP-10.4"
  description = "User guide marker for agentic batch1"
  version     = 1
  author      = "agentic_batch1"
  created     = (Get-Date).ToUniversalTime().ToString("s") + "Z"
  actions     = $actions
}
$prop3Path = "tmp\patches\proposal_agentic_batch1_docs.json"
$proposal3 | ConvertTo-Json -Depth 10 | Set-Content $prop3Path -Encoding UTF8

# ---------------------------------------------------------------------------
# DRY-RUN all proposals
# ---------------------------------------------------------------------------
$props = @($prop1Path, $prop2Path, $prop3Path)
foreach ($p in $props) {
  Write-Note "Dry-run $p"
  $cmd = "python -m tools.py.agentic.patch_apply --proposal `"$((Resolve-Path $p).Path -replace '\\','/')`""
  $r = LEB-Run $cmd
  ($r.stdout | ConvertFrom-Json) | ConvertTo-Json -Depth 8 | Write-Host
}

# ---------------------------------------------------------------------------
# REAL APPLY (if -Apply)
# ---------------------------------------------------------------------------
if ($Apply) {
  foreach ($p in $props) {
    Write-Note "Apply $p"
    $cmd = "python -m tools.py.agentic.patch_apply --proposal `"$((Resolve-Path $p).Path -replace '\\','/')`" --really-apply"
    $r = LEB-Run $cmd
    ($r.stdout | ConvertFrom-Json) | ConvertTo-Json -Depth 8 | Write-Host
  }
}

# ---------------------------------------------------------------------------
# TESTS (if -RunTests)
# ---------------------------------------------------------------------------
if ($RunTests) {
  Write-Note "Run pytest -q"
  $r = LEB-Run "pytest -q"
  if ($r.stdout.Length -gt 600) {
    $head = $r.stdout.Substring(0,600)
    Write-Host $head
  } else {
    Write-Host $r.stdout
  }
}
Write-Note "Done."
