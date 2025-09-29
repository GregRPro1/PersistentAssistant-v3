# Pack Fetcher (GitHub/URL)
## Setup
1. Set PAT on PC (read-only is ok): `setx PA_GITHUB_PAT "<token>"` then restart terminal.
2. Review `config/github_fetch.yaml` (defaults point to your repo).
3. Phone (GitHub Mobile): create/modify `control/next_pack.json` in the repo root.
   Examples:
   - `{"source":"url","url":"<public URL to a pack zip>","name":"PA_OUTPUT_TEST.zip"}`
   - `{"source":"release","tag":"pa-pack-123"}`
4. Run once: `pwsh tools\ps1\run_pack_fetcher.ps1 -Once`
   Or schedule: `pwsh tools\ps1\register_pack_fetcher.ps1`
Logs: `reports/ops/pack_fetcher.log`