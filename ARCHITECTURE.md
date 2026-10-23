# Architecture

> Public data from the Federal Housing Finance Agency, the Census Bureau (American Community Survey, Building Permits Survey, Population Estimates), the Department of Housing and Urban Development and the Consumer Financial Protection Bureau (HMDA), with mortgage rates from Freddie Mac under its terms of use. Metros are real and appear as they do in the public record; no household, borrower or address appears. The findings are a portfolio analysis, not financial advice, not a market forecast and not a fair lending finding.

```
  SOURCES        FHFA house price index master file (2000 to 2026Q2); the ACS one
                 year release by API (2005 to 2024, the 2020 gap carried as a gap);
                 HUD fair market rents and income limits; the Freddie Mac weekly rate
                 survey; Census building permits and population estimates with their
                 components; the HMDA extract (2018 to 2025); the OMB delineation
                 files by vintage; and the simulator
        v  contracts        typed frames, quarantine rules, provenance, definitions,
                            the delineation crosswalk by vintage
        v  warehouse        dbt staging to intermediate to marts; the metric layer
                            with its reconcile
        v  finance          payment, payment share, affordable price, affordable
                            share, breakeven, tested to the cent
        v  chapters         eight claims, each: plan hash, estimator proven on the
                            simulator, result with interval, chart, method note,
                            pushback
        v  loans            lock in intensity, the borrower pool, the metro map
        v  calculator       the check, the next quarter expectation, the score
   +------------------------------------------------------------------+
   |  EVALUATION (never grades itself)                                |
   |    the recovery study on the simulator per estimator and         |
   |    condition; claims tested on the registered split; intervals   |
   |    by block bootstrap over metros, lenders and years and by      |
   |    Monte Carlo over the census margins; Benjamini-Hochberg per   |
   |    family; the check log scored when the next quarter publishes  |
   +---------------------------+--------------------------------------+
                               v
  results/manifest.json    every number, interval, curve point and hash
        v  render           story, briefing, method notes, corrections, README,
                            RESULTS, these documents, the exports
   +------------------------------------------------------------------+
   |  FLY API       /v1/checks (affordability), /v1/score, /v1/audit   |
   |  GITHUB PAGES  the story, explore, rank, buyers, shocks, planner, |
   |                data, report                                       |
   +------------------------------------------------------------------+
```

## The packages

| Package | What it owns |
|---|---|
| `core` | the policy constants, the manifest and its formats, the statement, seeds and hashing |
| `contracts` | the typed frame of every source, the quarantine rules, the delineation crosswalk, the HMDA extract contract with its rounding rules |
| `sim` | the synthetic country: known incomes and distributions, elasticities, demand shocks with the reverse causality knob, the rate path, the lock in response, planted misreporting and suppression |
| `finance` | the amortization engine, the payment share, the affordable price, the breakeven engine with its cost model |
| `loans` | the lock in intensity, turnover, the borrower pool measures and the metro map through the vintages |
| `stats` | the block bootstrap, the Monte Carlo propagation of margins, cluster robust regression on the fixed effects solver, Benjamini-Hochberg, PELT, synthetic control with permutation inference |
| `chapters` | the eight plans and estimators, the panel they share, and the calculator marts |
| `evaluation` | the recovery study across conditions and seeds |
| `exports` | the workbook, the Tableau and Power BI specifications, the CSV bundle |
| `render` | the claim gate: every published document rendered from the manifest |
| `api` | the calculator and its check log |
| `pipeline` | the stages, in the order the Makefile runs them |

## Why every estimator is proven on a simulator first

The supply elasticity, the migration effect, the lock in response and the fair ranking each have a dozen ways to be subtly wrong: a window that lets builders answer the growth they are regressed on, a migration level that credits the pandemic with what a metro gained every year, a fixed effect that absorbs the very thing being ranked, an income bracket interpolated with the wrong tail. None of them can be checked on real metros, because the truth is not observed there; a wrong estimator produces a plausible number and nobody finds out. On the simulator the truth is written down before the data is generated, so an estimator that cannot recover it is known to be broken before it says anything about a city. Here that study graded 17 estimators 8,160 times across 24 conditions and 20 seeds. It found the supply regression attenuated toward zero when builders answer the price growth inside the window (+0.0026 mean bias with the demand control against a planted -0.025), and it found the migration regression on the level alone biased by -0.51% under strong reverse causality while the pre pandemic control held the bias at -0.02% and the placebo flagged that condition in only 46% of worlds; both findings are in the chapters in print.

## Why the story renders from the manifest

A story that can be edited by hand drifts from its evidence within a week: a number is rounded for a headline, a chart is regenerated, and the paragraph above it still quotes the old figure. Here every number in every published document is a template field filled from `results/manifest.json`, which only the pipeline writes. `make gates` renders every document again and diffs the whole file against what is committed, and a second check rejects any digit typed into a template outside a field. A number cannot reach a reader unless a query produced it, and when a query changes, every document that quotes it changes with it.

## Why prices are an index anchored to a level

The regulator publishes the movement of prices for every metro, quarterly, as an index with no dollars in it; the census publishes the level, the median value of owner occupied homes, once a year from a survey in which the owner states the value. Both are public domain. A dollar series from one vendor would be a single private estimate of both; the anchored series is the regulator's movement around the census level in one stated year, 2019, the last full response year before the pandemic. The anchor is a decision, so it is published with its sensitivity table (anchors in 2015, 2017, 2019 and 2023) beside every headline, and the self report check prints the census value over the transaction values in the loan extract for the same year, which bounds the bias the anchor carries without pretending to remove it.

## What runs where

The pipeline runs on one machine: DuckDB for the warehouse and the chapters, with the memory limit set below the machine for the loan extract, a disk cache keyed by input digest for the expensive steps, and every seeded step sorting before it samples so two runs agree to the byte. The raw files are fetched on a machine that can reach the government hosts, by a resumable script with a status file per source. The site is static on GitHub Pages and queries the committed marts in the browser with DuckDB-WASM. The API is one Fly machine that sleeps when idle, with its check log in Neon Postgres under its own schema; the site probes it twice and falls back to a recorded session, labeled as recorded, when it does not answer.
