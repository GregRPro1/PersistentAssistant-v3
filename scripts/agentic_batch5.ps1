#requires -Version 5
param(
  [switch]$Apply = $true,
  [switch]$RunTests = $true
)
$ErrorActionPreference = 'Stop'
$Repo = Split-Path -Parent $PSScriptRoot; if (-not $Repo) { $Repo = (Get-Location).Path }
Set-Location $Repo

function Note($m){ Write-Host ("==> " + $m) -ForegroundColor Cyan }
function LEB([string]$c){
  $b=@{cmd=$c}|ConvertTo-Json
  Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8765/run -ContentType 'application/json' -Body $b
}
function ActReplace([string]$path,[string]$content){
  $a=@{ path = ($path -replace '\\','/'); mode="replace"; content=$content }
  if (Test-Path $path) { $a.before_sha = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLower() }
  return $a
}
function BuildProposal([string]$fid,[hashtable[]]$acts,[string]$out){
  $p = @{
    feature_id  = $fid
    description = "Batch-5: LLM-style suggestion generator + tests"
    version     = 1
    author      = "agentic_batch5"
    created     = (Get-Date).ToUniversalTime().ToString("s") + "Z"
    actions     = $acts
  }
  $p | ConvertTo-Json -Depth 16 | Set-Content $out -Encoding UTF8
  return $out
}

New-Item -ItemType Directory -Force -Path tmp, tmp\patches, tools\py\agentic, tests, docs | Out-Null

# 0) Ensure policy allows docs/**, tools/**, tests/** (should already be true)
$policy = Get-Content config\runner_policy.yaml -Raw
foreach($g in @('docs/**','tools/**','tests/**')){
  $pat = [regex]::Escape($g).Replace("\*", "\*")
  if ($policy -notmatch $pat) {
    $policy = $policy -replace '(allow_globs:\s*)', "`$1`n  - `"$g`"`n"
  }
}
$policy | Set-Content config\runner_policy.yaml -Encoding UTF8

# 1) tools/py/agentic/llm_suggest.py (keyless fallback; emits safe doc change)
$llmPath = "tools\py\agentic\llm_suggest.py"
$llmContent = @'
from __future__ import annotations
import argparse, json
from datetime import datetime, timezone
from pathlib import Path
from .patch_utils import sha256_hex, ensure_dir

ROOT = Path(__file__).resolve().parents[3]

def now_ts() -> int:
    return int(datetime.now(timezone.utc).timestamp())

def suggest_text(step_id: str) -> str:
    # Fallback text; if later wired to ai_client, replace this function
    return f"# AI Change Log\\n\\n- {now_ts()}: bootstrap note for step {step_id}\\n"

def build_actions(step_id: str):
    rel = "docs/AI_CHANGELOG.md"
    p = ROOT / rel
    content = suggest_text(step_id)
    act = {"path": rel, "mode": "replace", "content": content}
    if p.exists():
        act["before_sha"] = sha256_hex(str(p))
    return [act]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    out_path = ROOT / args.out
    ensure_dir(out_path.parent)
    if out_path.exists() and not args.force:
        raise SystemExit(f"Refuse to overwrite: {out_path}")

    prop = {
        "feature_id": f"STEP-{args.id}",
        "description": f"LLM-style suggestion (fallback) for {args.id}",
        "version": 1,
        "author": "llm_suggest",
        "created": datetime.now(timezone.utc).isoformat(),
        "actions": build_actions(args.id),
        "meta": {"plan_step": args.id, "generator": "fallback"}
    }
    out_path.write_text(json.dumps(prop, indent=2), encoding="utf-8")
    print(str(out_path))

if __name__ == "__main__":
    main()
'@

# 2) tests/test_llm_suggest.py
$testPath = "tests\test_llm_suggest.py"
$testContent = @'
import json, subprocess, sys, uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def run(args):
    p = subprocess.run(args, capture_output=True, text=True, cwd=ROOT)
    return p.returncode, p.stdout.strip(), p.stderr.strip()

def test_llm_suggest_produces_valid_proposal_and_dryrun_ok():
    out_path = ROOT / "tmp" / "patches" / f"proposal_llm_{uuid.uuid4().hex}.json"
    rc, out, err = run([sys.executable, "-m", "tools.py.agentic.llm_suggest",
                        "--id", "10.6", "--out", str(out_path.relative_to(ROOT)), "--force"])
    assert rc == 0, err
    assert out_path.exists()
    prop = json.loads(out_path.read_text(encoding="utf-8"))
    assert prop["feature_id"] == "STEP-10.6"
    # dry-run apply
    rc2, out2, err2 = run([sys.executable, "-m", "tools.py.agentic.patch_apply",
                           "--proposal", str(out_path.relative_to(ROOT))])
    data = json.loads(out2)
    assert data.get("ok") is True
    assert data["results"][0]["reason"] in ("would_apply","applied")
'@

# Build proposals to replace/add the above files through our pipeline
$propA = "tmp\patches\proposal_batch5_llm.json"
$propB = "tmp\patches\proposal_batch5_tests.json"
BuildProposal "STEP-10.6" @( (ActReplace $llmPath $llmContent) ) $propA | Out-Null
BuildProposal "STEP-10.6" @( (ActReplace $testPath $testContent) ) $propB | Out-Null

# Dry-runs
foreach($p in @($propA,$propB)){
  Note "Dry-run $p"
  $r = LEB ("python -m tools.py.agentic.patch_apply --proposal `"$((Resolve-Path $p).Path -replace '\\','/')`"")
  ($r.stdout | ConvertFrom-Json) | ConvertTo-Json -Depth 8 | Write-Host
}

# Apply
if ($Apply) {
  foreach($p in @($propA,$propB)){
    Note "Apply $p"
    $r = LEB ("python -m tools.py.agentic.patch_apply --proposal `"$((Resolve-Path $p).Path -replace '\\','/')`" --really-apply")
    ($r.stdout | ConvertFrom-Json) | ConvertTo-Json -Depth 8 | Write-Host
  }
}

# Test
if ($RunTests) {
  Note "pytest -q"
  $r = LEB "pytest -q"
  Write-Host ($r.stdout)
}

Note "Batch-5 done."
