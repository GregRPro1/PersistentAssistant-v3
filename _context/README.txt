Context Tools
--------------
This directory holds master/child context summaries that persist across ChatGPT sessions.

Files installed by PAL20251012B_context_tools_pack at 2025-10-12 14:34:09:

- tools/context/context_loader.ps1   : Load master context; set env vars; write _context/active_context.yaml
- tools/context/context_capture.ps1  : Capture current child summary (repo, branch, commit, settings path, notes)
- tools/context/context_close.ps1    : Append closing notes to a child summary

Quickstart:
  # In PAL20251012A (old window), capture its summary:
  pwsh .\tools\context\context_capture.ps1 -MasterId PAL20251012 -ChildId PAL20251012A -Notes "Key lessons here..."

  # In a new window (PAL20251012B), load the master:
  pwsh .\tools\context\context_loader.ps1 -MasterId PAL20251012

  # When finishing PAL20251012B:
  pwsh .\tools\context\context_close.ps1 -MasterId PAL20251012 -ChildId PAL20251012B -Notes "B-window outcomes."

Notes:
- YAML is written in a simple format (no external modules).
- You can extend the capture script to include more fields (e.g., pack IDs) if desired.
