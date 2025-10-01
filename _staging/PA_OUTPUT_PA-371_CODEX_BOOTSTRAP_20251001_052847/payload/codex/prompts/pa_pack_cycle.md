# /pa_pack_cycle — Apply latest pack then validate

**Steps**:
1) Apply the latest pack zip in Downloads: `pwsh tools\ps1\codex\apply_latest_pack.ps1`.
2) Run `/pa_smoke` to validate.
3) If smokes fail, fix with targeted diffs and rerun.
4) If new scripts/endpoints exist, add/update tests under `tests/smoke`.
