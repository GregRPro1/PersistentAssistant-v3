# /pa_smoke — Run smoke tests and propose fixes

**Goal**: Run `pytest -q -m smoke`, summarize failures, propose minimal diffs, and re-run.

**Steps**:
1) Run: `pwsh tools\ps1\codex\smoke.ps1`.
2) If exit code != 0:
   - Parse the failure from the tail printed above.
   - Open and read the referenced files.
   - Propose minimal diffs (git-style unified) that fix the error.
   - Apply the diffs in-place.
   - Re-run step (1).
3) When green, write a short summary and stage changes: `git add -A`.
