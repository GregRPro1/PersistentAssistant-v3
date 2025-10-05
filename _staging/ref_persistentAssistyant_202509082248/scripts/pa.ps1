function Get-PAProposal {
  Get-ChildItem tmp\patches\proposal_*.json |
    Sort-Object LastWriteTime -Desc | Select -First 1
}

function PA-Propose([string]$id) {
  python -m tools.py.agentic.propose_for_step --id $id --out tmp\patches\proposal_step_$($id -replace '\.','_').json --force
}

function PA-PatchDry([string]$propPath) {
  $p = (Resolve-Path $propPath).Path -replace '\\','/'
  $cmd = "python -m tools.py.agentic.patch_apply --proposal `"$p`""
  Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8765/run -ContentType 'application/json' -Body (@{cmd=$cmd}|ConvertTo-Json)
}

function PA-PatchApply([string]$propPath) {
  $p = (Resolve-Path $propPath).Path -replace '\\','/'
  $cmd = "python -m tools.py.agentic.patch_apply --proposal `"$p`" --really-apply"
  Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8765/run -ContentType 'application/json' -Body (@{cmd=$cmd}|ConvertTo-Json)
}
