# PAL P3 Agentic Scaffold + Plan

This pack updates your **plan** and adds a minimal, provider-agnostic **Agentic Execution (P3)** scaffold:
- LLM adapters (`pal/adapters/llm/*`): base interface + OpenAI/Claude **stubs** (no network)
- VCS checks stub (`pal/adapters/vcs/github_checks.py`)
- Doc→YAML pipeline stub (`pal/pipelines/doc_to_yaml.py`) + runner (`pal/scripts/py/run_doc_to_yaml.py`)
- Smoke tests for **PAL-020..PAL-022**
- Convenience scripts to set P3 in-progress and run smokes

## Apply
```powershell
cd C:\_Repos\PersistentAssistant
pwsh .\scripts\apply_pack.ps1 -ZipPath "$env:USERPROFILE\Downloads\PAL_P3_Agentic_Scaffold_and_Plan.zip"
```

## Start P3 now (non-blocking)
```powershell
# turn P3 amber + refresh tracker
pwsh .\pal\scripts\ps\pal_start_p3.ps1

# run smokes in parallel (auto-flip to blue by watcher)
pwsh .\pal\scripts\ps\pal_smoke_p3.ps1
# ensure smoke watcher running:
Start-Job -ScriptBlock { pwsh .\pal\scripts\ps\smoke_watch.ps1 } | Out-Null
```

## Try doc→yaml pipeline (stubbed, no network)
```powershell
# Example: convert a text file using the openai stub
python .\pal\scripts\py\run_doc_to_yaml.py README.md openai
```
Generated: 2025-10-11
