# Serving

> Public data from the Federal Housing Finance Agency, the Census Bureau (American Community Survey, Building Permits Survey, Population Estimates), the Department of Housing and Urban Development and the Consumer Financial Protection Bureau (HMDA), with mortgage rates from Freddie Mac under its terms of use. Metros are real and appear as they do in the public record; no household, borrower or address appears. The findings are a portfolio analysis, not financial advice, not a market forecast and not a fair lending finding.

## The API

One FastAPI service (`packages/api`) in a container, with its check log in Neon Postgres under the `doorstep` schema and the calculator marts (`calc_metros.parquet`, `calc_quarters.parquet`, `calc_meta.json`) copied into the image from `results/marts`. The routes: `GET /v1/health`; `GET /v1/metros`; `GET /v1/curve` (the breakeven curve for a metro, income, down payment, rate and horizon); `POST /v1/checks` (token gated), which computes the answer, writes the check row, then the audit row, then returns the id; `GET /v1/checks` and `GET /v1/checks/{id}`; `POST /v1/score` (token gated), which scores stored checks whose next quarter has published against the realised payment share; `GET /v1/scorecard`; `GET /v1/audit`. Every response carries the statement and the rate attribution. A write without the token is refused with HTTP 401; a machine that is waking answers its first request with HTTP 503 and the site probes twice.

The live deployment: not yet deployed.

## What is stored

A check stores the metro code, the income rounded to the nearest thousand, the down payment share, the rate, the horizon, the quarter it rests on, the answers and the carry forward expectation of next quarter's payment share; never a name, an email or an address. The planted identifier scan (`scripts/scan_for_planted_identifiers.py`) seeds the fixtures with identifiers and asserts none reaches the published data or the API.

## Latency

Live latency not measured. Local latency not measured.
## The site

Static export of the Next.js app on GitHub Pages at not yet published, reading the committed marts in the browser through DuckDB-WASM. The test server (`web/scripts/serve.mjs`) refuses HEAD and answers the first mock API request with HTTP 503, the way the host and the Fly machine behave, and the Playwright suite runs against it. The live check in a real browser (no browser yet, not yet): not checked, 0 of 0 routes loaded with the statement; with the API asleep: not observed.

## Operations

The container runs on whichever free host holds it: `fly.toml` and `deploy/deploy.ps1` deploy it to Fly.io, and `.github/workflows/space.yml` publishes the same image to a Hugging Face Docker Space (free, no card) when the repository holds an `HF_TOKEN` secret and an `HF_SPACE` variable; the Space takes the secrets `DATABASE_URL`, `DOORSTEP_WRITE_TOKEN` and `DOORSTEP_DB_SCHEMA` and the variable `DOORSTEP_CORS_ORIGINS` in its settings. Verify, replay, reset and the load test are PowerShell scripts under `deploy/`, run from the machine that holds the Neon connection string against whichever base URL `deploy/live-url.txt` names. `deploy/verify.ps1` writes `results/deploy/verification.json`, which the manifest records as the separate client check; `deploy/replay.ps1` preloads the demo queue with checks for the twenty largest metros at the median income and scores them; `deploy/reset.ps1` clears the checks the recording created, which the rederive step runs before the tag.
