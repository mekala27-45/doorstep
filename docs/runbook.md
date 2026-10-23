# Runbook

> Public data from the Federal Housing Finance Agency, the Census Bureau (American Community Survey, Building Permits Survey, Population Estimates), the Department of Housing and Urban Development and the Consumer Financial Protection Bureau (HMDA), with mortgage rates from Freddie Mac under its terms of use. Metros are real and appear as they do in the public record; no household, borrower or address appears. The findings are a portfolio analysis, not financial advice, not a market forecast and not a fair lending finding.

## Fetch

`deploy/fetch-data.ps1 <mode>` runs on a machine that can reach the government hosts, one request at a time with retries and a resume on restart, and writes `fetch-status-<mode>.json` beside the data: `core` (FHFA, PMMS, HUD, permits, population, delineations, the gazetteer), `acs` (every table for every year from 2005, with a free Census API key in `CENSUS_API_KEY`; the API has slow nights, and a year whose tables time out is filled by running the mode again) and `hmda` (one file per year from 2018, filtered as it is read). The status files are copied under `data/external` so the manifest can prove the window ends at the latest release (3 status files in the last run).

## Build

```
make data          # data/derived parquet per source, data/hmda parquet per year, the quarantine report
make warehouse     # dbt build and test; results/marts
make metrics       # the reconcile; fails on a disagreement
make simulate      # data/sim: the demonstration country and its truth
make recovery      # results/recovery; cached under .cache/recovery by source digest
make chapters      # results/chapters, results/charts, the calculator marts; plans registered first
make exports       # exports/workbook.xlsx, exports/tableau, exports/powerbi, exports/csv
make manifest      # results/manifest.json merged from every stage
make render        # story/story.md, report/briefing.*, README.md, RESULTS.md, docs/*
make marts         # web/public/data for the site
make gates         # dash, vocabulary, statement, claim gate, identifier scan, palette
```

Each stage writes its own partial manifest, so a stage can be rerun alone; `make manifest render` picks the new numbers up everywhere. The chapters stage refuses to run when a plan has changed since it was registered: delete `results/chapters/plans.json` on purpose and say why in DECISIONS.md.

## When a step stops

- **The data stage stops on a contract error.** The message names the source, the file and the rule; the file is usually a new vintage with a changed layout. Fix the contract in `packages/contracts`, bump nothing, rerun.
- **The warehouse stops on a dbt test.** `warehouse/target/run_results.json` names the test; the cause is usually a quarantine flag that a model forgot to carry. The build does not delete rows to pass a test.
- **The reconcile stops on a disagreement.** `results/metrics/reconcile.json` lists the metric, the grain and the cell; the mart dropped a filter or double counted a join.
- **The chapters stage stops on a registration error.** The plan changed; see above.
- **The claim gate stops on drift.** A document on disk differs from its render; run `make render` and commit, or find the digit typed into a template.
- **The API will not start.** `DATABASE_URL` and `DOORSTEP_WRITE_TOKEN` are the two secrets; `alembic upgrade head` runs in the image at start; the calculator marts must be present in `results/marts`.

## Deploy

`deploy/deploy.ps1` builds and deploys the API image to Fly and runs the migration, or the `space` workflow publishes the same image to a Hugging Face Docker Space (the free route, no card: an `HF_TOKEN` secret and an `HF_SPACE` variable on the repository, the Space's own secrets for the database and the write token); either way `deploy/live-url.txt` holds the base URL the other scripts read; `deploy/verify.ps1` checks it from a separate client and writes `results/deploy/verification.json`; `deploy/replay.ps1` preloads the demo queue; `scripts/load_test.py --base-url ...` measures latency into `results/latency`; `scripts/live_check.py` records the browser check into `results/live_check.json`. Then `make manifest render` and commit.

## Rederive

`scripts/reset_and_rederive.py` creates a worktree, runs every stage from the raw files with the caches cleared, compares every manifest value with the committed one and writes `results/rederive.json`; the tag is not cut until it reports zero drift. It also clears the checks the demo recording created through `deploy/reset.ps1`.
