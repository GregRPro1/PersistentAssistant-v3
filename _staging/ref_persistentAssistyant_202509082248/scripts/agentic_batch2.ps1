#requires -Version 5
param([switch]$Apply = $true, [switch]$RunTests = $true)

$ErrorActionPreference = 'Stop'

# --- helpers ---
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

# --- cwd to repo root ---
$Repo = Split-Path -Parent $PSScriptRoot
if (-not $Repo) { $Repo = (Get-Location).Path }
Set-Location $Repo

# --- make tmp dirs ---
Note "Prep folders"
New-Item -ItemType Directory -Force -Path tmp, tmp\patches, tmp\context | Out-Null

# --- context_pack.py ---
Note "Write tools\py\agentic\context_pack.py"
$ctxPath = "tools\py\agentic\context_pack.py"
$ctxContent = @'
from __future__ import annotations
import argparse, json, hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

def sha256_hex(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()

def add_file(files: list[dict], rel: str) -> None:
    p = (ROOT / rel).resolve()
    if p.exists() and p.is_file():
        files.append({
            "rel": rel.replace("\\\\","/"),
            "bytes": p.stat().st_size,
            "sha256": sha256_hex(p),
        })

def build_pack(plan_path: Path) -> dict:
    files: list[dict] = []
    # always include plan + policy
    add_file(files, "project/plans/project_plan_v3.yaml")
    add_file(files, "config/runner_policy.yaml")
    # helpful docs
    for rel in ["docs/USER_GUIDE.md", "docs/GLOSSARY.md"]:
        add_file(files, rel)
    # agentic code
    agdir = ROOT / "tools/py/agentic"
    if agdir.exists():
        for p in sorted(agdir.glob("*.py")):
            try:
                rel = p.relative_to(ROOT).as_posix()
                add_file(files, rel)
            except Exception:
                pass
    return {
        "root": str(ROOT),
        "plan": str(plan_path),
        "files": files,
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", default=str(ROOT / "project/plans/project_plan_v3.yaml"))
    ap.add_argument("--out",  default=str(ROOT / "tmp/context/context_pack.json"))
    args = ap.parse_args()
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    pack = build_pack(Path(args.plan))
    out.write_text(json.dumps(pack, indent=2), encoding="utf-8")
    print(str(out))

if __name__ == "__main__":
    main()
'@
Write-Utf8File $ctxPath $ctxContent

# --- test_context_pack.py ---
Note "Write tests\test_context_pack.py"
$testPath = "tests\test_context_pack.py"
$testContent = @'
import json, subprocess, sys, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]

def run(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True)
    return p.returncode, p.stdout, p.stderr

def test_context_pack_smoke():
    out = ROOT / "tmp/context/context_pack.json"
    if out.exists():
        out.unlink()
    rc, out_str, err = run([sys.executable, "-m", "tools.py.agentic.context_pack", "--out", str(out)])
    assert rc == 0, err
    assert out.exists(), "context pack json not created"
    data = json.loads(out.read_text(encoding="utf-8"))
    assert "files" in data and isinstance(data["files"], list)
    rels = { f["rel"] for f in data["files"] }
    assert "project/plans/project_plan_v3.yaml" in rels
    assert "config/runner_policy.yaml" in rels
'@
Write-Utf8File $testPath $testContent

# --- (optional) tiny policy tweak for this batch (allow tests/**, tools/** already typical) ---
Note "Ensure policy allows tools/** & tests/** (idempotent)"
$polPath = "config\runner_policy.yaml"
if (Test-Path $polPath) {
    $pol = Get-Content $polPath -Raw
    if ($pol -notmatch 'allow_globs:\s*[^#\r\n]*(\r?\n)\s*-\s*"tests/\*\*"') {
        $pol = $pol -replace 'allow_globs:\s*\r?\n', "allow_globs:`r`n  - `"tests/**`"`r`n"
        $pol | Set-Content $polPath -Encoding UTF8
    }
}

# --- run tests through LEB ---
if ($RunTests) {
    Note "pytest -q tests/test_context_pack.py"
    $r = LEB "pytest -q tests/test_context_pack.py"
    # surface the test output
    $r.stdout
    if ($r.rc -ne 0) { throw "pytest failed (context_pack)" }
}

Note "Batch 2 complete"
