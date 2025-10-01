PA-371 Codex Bootstrap (20251001_052847)

Adds:
- tools\ps1\codex\helpers (smoke, watchdog ops, tunnel URL, apply-pack)
- codex\prompts\ (/pa_smoke, /pa_watchdog, /pa_pack_cycle) — copied to ~/.codex/prompts if possible

Use:
  npm i -g @openai/codex  (or: winget install OpenAI.CodexCLI)
  codex   # run from repo root
  Then type: /pa_smoke  OR  /pa_watchdog  OR  /pa_pack_cycle
