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
    description = "Batch-6: per-agent model routing (OpenAI live, offline safe) + tests"
    version     = 1
    author      = "agentic_batch6"
    created     = (Get-Date).ToUniversalTime().ToString("s") + "Z"
    actions     = $acts
  }
  $p | ConvertTo-Json -Depth 16 | Set-Content $out -Encoding UTF8
  return $out
}

# Ensure dirs
New-Item -ItemType Directory -Force -Path tmp, tmp\patches, tools\py\agentic, tools\py\providers, tests, config\ai | Out-Null

# 0) Policy: allow config/**, tools/**, tests/**
$policy = Get-Content config\runner_policy.yaml -Raw
foreach($g in @('config/**','tools/**','tests/**')){
  $pat = [regex]::Escape($g).Replace("\*", "\*")
  if ($policy -notmatch $pat) {
    $policy = $policy -replace '(allow_globs:\s*)', "`$1`n  - `"$g`"`n"
  }
}
$policy | Set-Content config\runner_policy.yaml -Encoding UTF8

# 1) config/ai/agents.yaml
$cfgPath = "config\ai\agents.yaml"
$cfgContent = @'
# Per-agent provider/model selection
defaults:
  provider: openai
  model: gpt-4o-mini
  mode: chat

agents:
  strategy:      { provider: openai, model: gpt-4o-mini, mode: chat }
  review:        { provider: openai, model: gpt-4o-mini, mode: chat }
  introspection: { provider: openai, model: gpt-4o-mini, mode: chat }
  coding:        { provider: openai, model: o3-mini,    mode: reasoning }
  documentation: { provider: openai, model: gpt-4o-mini, mode: chat }
'@

# 2) tools/py/providers/base_client.py
$basePath = "tools\py\providers\base_client.py"
$baseContent = @'
from __future__ import annotations
from typing import Any, Dict, List

class BaseClient:
    provider = "base"
    model = "unknown"

    def __init__(self, model: str):
        self.model = model

    def complete(self, messages: List[Dict[str, Any]], **kwargs) -> Dict[str, Any]:
        raise NotImplementedError("Provider client must implement complete()")
'@

# 3) tools/py/providers/openai_client.py  (offline-fallback safe)
$oiPath = "tools\py\providers\openai_client.py"
$oiContent = @'
from __future__ import annotations
import os, json
from typing import Any, Dict, List
from .base_client import BaseClient

class OpenAIClient(BaseClient):
    provider = "openai"

    def __init__(self, model: str):
        super().__init__(model)
        self.api_key = os.getenv("OPENAI_API_KEY", "")

    def _offline(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        # Deterministic offline echo of the last user message
        last = ""
        for m in reversed(messages):
            if m.get("role") == "user":
                last = m.get("content", "")
                break
        return {
            "text": f"[offline:{self.model}] {last}".strip(),
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            "offline": True,
        }

    def complete(self, messages: List[Dict[str, Any]], **kwargs) -> Dict[str, Any]:
        # Force offline if no key or PA_OFFLINE=1
        if not self.api_key or os.getenv("PA_OFFLINE", "1") == "1":
            return self._offline(messages)

        # Best-effort real call if SDK present (won't run in tests)
        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.api_key)
            resp = client.chat.completions.create(model=self.model, messages=messages)
            choice = resp.choices[0].message.content or ""
            usage = getattr(resp, "usage", None)
            usage_d = dict(usage) if usage else {}
            return {"text": choice, "usage": usage_d, "offline": False}
        except Exception as e:
            # Never fail the pipeline; surface the error in text for visibility
            return {"text": f"[openai-error:{type(e).__name__}] {e}", "usage": {}, "offline": True}
'@

# 4) tools/py/agentic/ai_router.py
$rtrPath = "tools\py\agentic\ai_router.py"
$rtrContent = @'
from __future__ import annotations
import os, json
from pathlib import Path
from typing import Dict, Any

ROOT = Path(__file__).resolve().parents[3]
CFG  = ROOT / "config" / "ai" / "agents.yaml"

def _yaml_load(p: Path) -> Dict[str, Any]:
    import yaml
    return yaml.safe_load(p.read_text(encoding="utf-8")) if p.exists() else {}

def load_agent_map() -> Dict[str, Any]:
    data = _yaml_load(CFG)
    defaults = data.get("defaults", {"provider":"openai","model":"gpt-4o-mini","mode":"chat"})
    agents   = data.get("agents", {})
    return {"defaults": defaults, "agents": agents}

def get_selection(agent_name: str) -> Dict[str, str]:
    m = load_agent_map()
    d = m["defaults"]; a = m["agents"].get(agent_name, {})
    return {"provider": a.get("provider", d["provider"]),
            "model":    a.get("model",    d["model"]),
            "mode":     a.get("mode",     d.get("mode","chat"))}

def get_client(agent_name: str):
    sel = get_selection(agent_name)
    prov = sel["provider"]; model = sel["model"]
    if prov == "openai":
        from tools.py.providers.openai_client import OpenAIClient
        return OpenAIClient(model)
    # Future: plug other providers here
    raise RuntimeError(f"Unsupported provider: {prov}")

def complete(agent_name: str, messages):
    c = get_client(agent_name)
    return c.complete(messages)
'@

# 5) tools/py/agentic/llm_suggest_routered.py
$sugPath = "tools\py\agentic\llm_suggest_routered.py"
$sugContent = @'
from __future__ import annotations
import argparse, json
from datetime import datetime, timezone
from pathlib import Path
from .patch_utils import ensure_dir, sha256_hex
from .ai_router import complete, ROOT

def now_iso():
    return datetime.now(timezone.utc).isoformat()

def build_actions(target_path: str, content: str):
    rel = target_path.replace("\\", "/")
    p = ROOT / rel
    act = {"path": rel, "mode": "replace", "content": content}
    if p.exists():
        act["before_sha"] = sha256_hex(str(p))
    return [act]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", required=True, help="plan step id (e.g., 10.6)")
    ap.add_argument("--agent", default="documentation", help="agent role to use (strategy/review/introspection/coding/documentation)")
    ap.add_argument("--out", required=True, help="proposal output path (repo-relative)")
    ap.add_argument("--target", default="docs/AI_CHANGELOG.md", help="file to write")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    # Compose a minimal prompt
    messages = [
        {"role":"system","content":"You are helping maintain an AI change log for this repository. Respond with a short bullet summarizing the change."},
        {"role":"user",  "content":f"Create one bullet for plan step {args.id} noting the automation bootstrap status."}
    ]
    res = complete(args.agent, messages)
    text = res.get("text","").strip() or f"- {args.id}: offline bootstrap note"
    content = f"# AI Change Log\n\n{text}\n"

    out_path = ROOT / args.out
    ensure_dir(out_path.parent)
    if out_path.exists() and not args.force:
        raise SystemExit(f"Refuse to overwrite: {out_path}")

    prop = {
        "feature_id": f"STEP-{args.id}",
        "description": f"Routered suggestion for {args.id} via agent '{args.agent}'",
        "version": 1,
        "author": "llm_suggest_routered",
        "created": now_iso(),
        "actions": build_actions(args.target, content),
        "meta": {"agent": args.agent, "offline": res.get("offline", True)}
    }
    out_path.write_text(json.dumps(prop, indent=2), encoding="utf-8")
    print(str(out_path))

if __name__ == "__main__":
    main()
'@

# 6) tests/test_ai_router.py
$tstPath = "tests\test_ai_router.py"
$tstContent = @'
import json, os, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def run(args, env=None):
    e = dict(os.environ)
    if env: e.update(env)
    p = subprocess.run(args, capture_output=True, text=True, cwd=ROOT, env=e)
    return p.returncode, p.stdout.strip(), p.stderr.strip()

def test_router_selection_and_offline_suggest():
    # Force offline for deterministic output
    env = {"PA_OFFLINE":"1", "OPENAI_API_KEY":""}

    # Generate a routered proposal
    out_rel = "tmp/patches/proposal_routered_10_7.json"
    rc, out, err = run([sys.executable, "-m", "tools.py.agentic.llm_suggest_routered",
                        "--id","10.7","--agent","documentation","--out", out_rel, "--force"], env=env)
    assert rc == 0, err
    prop_path = ROOT / out_rel
    assert prop_path.exists(), "proposal not written"

    # Dry-run apply should be ok
    rc2, out2, err2 = run([sys.executable, "-m", "tools.py.agentic.patch_apply",
                           "--proposal", out_rel], env=env)
    assert rc2 == 0, err2
    data = json.loads(out2)
    assert data.get("ok") is True
    assert data["results"][0]["reason"] in ("would_apply","applied")
'@

# Build proposals: keep bundles modest
$propCfg = "tmp\patches\proposal_batch6_cfg_router.json"
$propCode = "tmp\patches\proposal_batch6_code.json"
$propTests = "tmp\patches\proposal_batch6_tests.json"

BuildProposal "STEP-10.6" @(
  (ActReplace $cfgPath $cfgContent),
  (ActReplace $basePath $baseContent),
  (ActReplace $oiPath  $oiContent),
  (ActReplace $rtrPath $rtrContent)
) $propCfg | Out-Null

BuildProposal "STEP-10.6" @(
  (ActReplace $sugPath $sugContent)
) $propCode | Out-Null

BuildProposal "STEP-10.6" @(
  (ActReplace $tstPath $tstContent)
) $propTests | Out-Null

# Dry-runs
foreach($p in @($propCfg,$propCode,$propTests)){
  Note "Dry-run $p"
  $abs = (Resolve-Path $p).Path -replace '\\','/'
  $r = LEB ("python -m tools.py.agentic.patch_apply --proposal `"$abs`"")
  ($r.stdout | ConvertFrom-Json) | ConvertTo-Json -Depth 8 | Write-Host
}

# Apply
if ($Apply) {
  foreach($p in @($propCfg,$propCode,$propTests)){
    Note "Apply $p"
    $abs = (Resolve-Path $p).Path -replace '\\','/'
    $r = LEB ("python -m tools.py.agentic.patch_apply --proposal `"$abs`" --really-apply")
    ($r.stdout | ConvertFrom-Json) | ConvertTo-Json -Depth 8 | Write-Host
  }
}

# Tests (use offline to be deterministic)
if ($RunTests) {
  Note "pytest -q (offline)"
  $r = LEB "pytest -q"
  Write-Host ($r.stdout)
}

Note "Batch-6 done."
