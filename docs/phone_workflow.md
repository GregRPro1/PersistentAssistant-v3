# Phone-first Approval Workflow (Recommended)

## Option A — Stable Tag (no JSON, easiest)
1. On iPhone (Safari): Repo → Releases → create (once) or open tag **PA-OUTPUT**.
2. Edit release → remove old assets → upload new `PA_OUTPUT_<anything>.zip` → Update.
3. PC fetcher (scheduled) will detect and apply automatically.

## Option B — Control File + URL (great with ChatGPT links)
1. On iPhone (GitHub Mobile): Add file `control/next_pack.json` at repo root:
   ```json
   {"source":"url","url":"<direct pack URL>","name":"PA_OUTPUT_<anything>.zip"}
   ```
2. Commit to `main`. The PC fetcher will download the URL and apply.

## Getting Status on Your Phone
- Quick: check `reports/ops/pack_fetcher.log` and `reports/ops/hello_pack_applied.txt` in the repo.
- Next step (to be added): PC will publish `reports/ops/status.md` and `docs/ops/index.html` (GitHub Pages) after each run for a clean phone view.