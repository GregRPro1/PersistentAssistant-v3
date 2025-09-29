# Phone-first Approval + Feedback (v1)

## Approve from phone (stable tag)
- Repo → Releases → tag **PA-OUTPUT** → Edit → upload new `PA_OUTPUT_*.zip` → Update.

## Approve from phone (URL control)
- File `control/next_pack.json` on `main`:
  `{"source":"url","url":"<direct pack URL>","name":"PA_OUTPUT_<anything>.zip"}`

## Get feedback on phone
- Check `reports/ops/pack_fetcher.log` and `reports/ops/hello_pack_applied.txt`.
- Next: we’ll add `reports/ops/status.md` and `docs/ops/index.html` (phone-friendly).

## Keep it safe
- Only accept `PA_OUTPUT_*.zip` you trust.
- Prefer Github Releases (immutable assets) + optional `.sha256` verification (coming).
- Keep the repo public only if you’re comfortable with exposure; otherwise use a read-only PAT on the PC.