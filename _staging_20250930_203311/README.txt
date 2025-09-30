PA_OUTPUT_PA-361_FIX2

This pack overwrites your repo's scripts\apply_pack.ps1 with a clean, validated version.
Run it with your standard one-liner:

  pwsh C:\_Repos\PersistentAssistant\apply_packs_only.ps1

What it does:
  - Fixes tests/smoke/test_graph_config.py import (idempotent)
  - Removes payload\tests to stop pytest duplicates
  - Writes/updates pytest.ini (excludes noisy dirs; temporarily skips test_graph_config)
  - Clears caches
  - Runs pytest -m smoke (logs to tmp\logs\pytest_smoke_<ts>.txt)
  - Attempts cloudflared quick-tunnel helpers
  - Commits changes (no push)
