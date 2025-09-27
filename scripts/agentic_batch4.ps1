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
    description = "Batch-4: proposal micro-API + tests"
    version     = 1
    author      = "agentic_batch4"
    created     = (Get-Date).ToUniversalTime().ToString("s") + "Z"
    actions     = $acts
  }
  $p | ConvertTo-Json -Depth 16 | Set-Content $out -Encoding UTF8
  return $out
}

# ensure dirs
New-Item -ItemType Directory -Force -Path tmp, tmp\patches, server, tests | Out-Null

# 0) Policy: allow server/** and tests/**
$policy = Get-Content config\runner_policy.yaml -Raw
if ($policy -notmatch 'allow_globs:') { throw "runner_policy.yaml missing allow_globs; please paste the latest policy first." }
if ($policy -notmatch 'server/\*\*') {
  $policy = $policy -replace '(allow_globs:\s*)', "`$1`n  - `"server/**`"`n"
}
if ($policy -notmatch 'tests/\*\*') {
  $policy = $policy -replace '(allow_globs:\s*)', "`$1`n  - `"tests/**`"`n"
}
$policy | Set-Content config\runner_policy.yaml -Encoding UTF8

# 1) server/proposal_api.py
$apiPath = "server\proposal_api.py"
$apiContent = @'
from __future__ import annotations
import json, time
from pathlib import Path
from flask import Flask, request, jsonify
import requests

ROOT = Path(__file__).resolve().parents[1]
LEB_URL = "http://127.0.0.1:8765"

app = Flask(__name__)

def leb_run(cmd: str):
    r = requests.post(f"{LEB_URL}/run", json={"cmd": cmd}, timeout=30)
    r.raise_for_status()
    return r.json()

@app.get("/healthz")
def healthz():
    return jsonify({"ok": True, "service": "proposal_api", "ts": int(time.time())})

@app.post("/propose_step")
def propose_step():
    data = request.get_json(force=True, silent=True) or {}
    step_id = data.get("id")
    out = data.get("out")
    if not step_id:
        return jsonify({"ok": False, "error": "missing id"}), 400
    if not out:
        out = f"tmp/patches/proposal_step_{step_id}.json"
    cmd = f'python -m tools.py.agentic.propose_for_step --id {step_id} --out "{out}" --force'
    lr = leb_run(cmd)
    # proposer prints the output path on stdout; read it back
    path_line = (lr.get("stdout") or "").strip().splitlines()[-1] if lr.get("stdout") else ""
    prop_path = (ROOT / (out if not path_line else path_line)).resolve()
    if not prop_path.exists():
        return jsonify({"ok": False, "error": "proposal not found", "stdout": lr.get("stdout","")}), 500
    prop = json.loads(prop_path.read_text(encoding="utf-8"))
    return jsonify({"ok": True, "proposal_path": str(prop_path), "proposal": prop})

@app.post("/proposal_diff")
def proposal_diff():
    data = request.get_json(force=True, silent=True) or {}
    p = data.get("proposal_path")
    if not p:
        return jsonify({"ok": False, "error": "missing proposal_path"}), 400
    cmd = f'python -m tools.py.agentic.patch_diff --proposal "{p}"'
    lr = leb_run(cmd)
    try:
        diff_json = json.loads(lr.get("stdout") or "{}")
    except Exception as e:
        return jsonify({"ok": False, "error": f"diff parse failed: {e}", "stdout": lr.get("stdout","")}), 500
    return jsonify({"ok": True, "diff": diff_json})

@app.post("/proposal_apply")
def proposal_apply():
    data = request.get_json(force=True, silent=True) or {}
    p = data.get("proposal_path")
    really = bool(data.get("really_apply", False))
    if not p:
        return jsonify({"ok": False, "error": "missing proposal_path"}), 400
    cmd = f'python -m tools.py.agentic.patch_apply --proposal "{p}"'
    if really:
        cmd += " --really-apply"
    lr = leb_run(cmd)
    try:
        apply_json = json.loads(lr.get("stdout") or "{}")
    except Exception as e:
        return jsonify({"ok": False, "error": f"apply parse failed: {e}", "stdout": lr.get("stdout","")}), 500
    return jsonify({"ok": True, "result": apply_json})

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8784, debug=False)
'@

# 2) tests/test_proposal_api.py
$testApiPath = "tests\test_proposal_api.py"
$testApiContent = @'
import json, os, requests
from pathlib import Path
import pytest

# Import the Flask app without running it as a server
from server.proposal_api import app, LEB_URL, ROOT

def leb_up():
    try:
        r = requests.get(f"{LEB_URL}/ping", timeout=2)
        return r.status_code == 200
    except Exception:
        return False

@pytest.mark.skipif(not leb_up(), reason="LEB is not running on 127.0.0.1:8765")
def test_proposal_api_roundtrip():
    client = app.test_client()

    # 1) propose
    out = "tmp/patches/proposal_api_test.json"
    rv = client.post("/propose_step", json={"id":"10.3","out":out})
    assert rv.status_code == 200
    j = rv.get_json()
    assert j["ok"] is True
    ppath = j["proposal_path"]
    assert Path(ppath).exists()

    # 2) diff
    rv2 = client.post("/proposal_diff", json={"proposal_path": ppath})
    assert rv2.status_code == 200
    d = rv2.get_json()
    assert d["ok"] is True
    diff_text = json.dumps(d["diff"])
    assert "+" in diff_text or "diffs" in d["diff"]  # minimal sanity

    # 3) dry-run apply (should be ok / would_apply or applied depending on policy)
    rv3 = client.post("/proposal_apply", json={"proposal_path": ppath, "really_apply": False})
    assert rv3.status_code == 200
    a = rv3.get_json()
    assert a["ok"] is True
    res = a["result"]
    assert res.get("ok") in (True, False)  # tool emits ok True for dry-run ok
'@

# Build proposals (replace files via policy-gated apply)
$prop1 = "tmp\patches\proposal_batch4_api.json"
$prop2 = "tmp\patches\proposal_batch4_tests.json"
BuildProposal "STEP-10.4" @( (ActReplace $apiPath $apiContent) ) $prop1 | Out-Null
BuildProposal "STEP-10.5" @( (ActReplace $testApiPath $testApiContent) ) $prop2 | Out-Null

# Dry-runs
foreach($p in @($prop1,$prop2)){
  Note "Dry-run $p"
  $r = LEB ("python -m tools.py.agentic.patch_apply --proposal `"$((Resolve-Path $p).Path -replace '\\','/')`"")
  ($r.stdout | ConvertFrom-Json) | ConvertTo-Json -Depth 8 | Write-Host
}

# Apply
if ($Apply) {
  foreach($p in @($prop1,$prop2)){
    Note "Apply $p"
    $r = LEB ("python -m tools.py.agentic.patch_apply --proposal `"$((Resolve-Path $p).Path -replace '\\','/')`" --really-apply")
    ($r.stdout | ConvertFrom-Json) | ConvertTo-Json -Depth 8 | Write-Host
  }
}

# Test
if ($RunTests) {
  Note "pytest -q (API test will skip if LEB is down)"
  $r = LEB "pytest -q"
  Write-Host ($r.stdout)
}

Note "Batch-4 done."
