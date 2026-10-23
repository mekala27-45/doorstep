# doorstep

**Can anyone still afford a home: a data story in 8 chapters, built on every metropolitan area present in both the regulator price index and the census one year release, 393 of them, from 2000 to 2026Q2.**

The window opens in 2000 with the first quarter of the price index and the first year of the permits and population files, and runs to the latest quarter the Federal Housing Finance Agency has published (2026Q2); the census one year release runs from its first year, 2005, to the latest, 2024, and the 2020 release does not exist, so that year is carried as a gap and every series that crosses it breaks; the mortgage disclosure extract runs from 2018, the first year of the current reporting rule, to 2025, the latest year published. Every row inside the window is used and nothing is sampled: 85,272 index rows, 2,415,786 census estimates with their margins over 19 releases, 2,900 weekly rate observations, 81,768 permit rows, 81,714 county population rows and 137,678,531 mortgage records. The extract is the one subset, stated here as the spec asks: the fetch keeps originated loans (action_taken = 1 and loan_purpose in (1, 31, 32)), 64,743,292 rows, and the analysis keeps the ones with a usable income, rate and term (occupancy_type = 1 (principal residence); reverse mortgages, open end lines and business purpose loans flagged), 55,817,457 rows, with the excluded rows counted in the quarantine report rather than deleted. Micropolitan areas are carried in the warehouse and shown in the explorer and are excluded from the ranking, because the one year release covers only the largest of them. Mandatory steps not yet done: 7, 13, 14, 15, 16, 18 (numbered as in the checklist below); the build is not called complete until that list is empty.
- **The story:** not yet published
- **The affordability calculator's API:** not yet deployed.
- **The briefing:** [report/briefing.md](report/briefing.md), rendered from the same manifest as the site

> Public data from the Federal Housing Finance Agency, the Census Bureau (American Community Survey, Building Permits Survey, Population Estimates), the Department of Housing and Urban Development and the Consumer Financial Protection Bureau (HMDA), with mortgage rates from Freddie Mac under its terms of use. Metros are real and appear as they do in the public record; no household, borrower or address appears. The findings are a portfolio analysis, not financial advice, not a market forecast and not a fair lending finding.

## The eight findings

| Chapter | The finding | The number |
|---|---|---|
| Affordable is a decision | The payment share of 2024 does not exceed 2023; the payment story is not yet the largest the window has seen. It sits +1.1 pts above 2006 (interval +1.0 pts to +1.3 pts), so the 2006 peak is passed, and the window's own peak is 2023. | payment share 34.9% in 2024 (34.8% to 35.0%), +1.1 pts against the 2006 peak; price to income +3.4% over the span |
| The rate shock and the lock in | The rate part of the payment overtook the price part in 2023Q3. The rate shock froze turnover where owners had the most to lose: 0.06 fewer purchases per 100 owner households per point of lock in (interval -0.08 to -0.03), and the placebo on the years before the shock sits at 0.00 with an interval that includes zero. | rate part 40% of the payment change since 2019Q1, overtaking in 2023Q3; lock in -0.056 per point (-0.077 to -0.034), placebo +0.001 |
| The rent burden is a distribution problem | The median renter is burdened in 51% of metros in 2024, so the median hides nothing; the problem is the whole distribution, with 26.5% of renters paying half or more (interval 25.7% to 27.2%). The national series moved and stayed moved in 2009, 2015, 2021. | severe share 26.5% (25.7% to 27.2%); breaks in 2009, 2015, 2021 |
| Where builders kept pace, prices rose less | Where builders kept pace, prices rose less: 8.0% less price growth over 5 years per extra permit per hundred households (interval -14.3% to -1.7%); without the demand control the estimate is -0.4%. | -8.0% per window per extra permit per hundred households (-14.3% to -1.7%); -0.4% without the demand control |
| The fair ranking | The ranking changes when you hold constant what people earn there: 17 of the 20 largest metros move beyond their intervals. Less affordable than their price says: Tampa-St. Petersburg-Clearwater from 106 to 90; Miami-Fort Lauderdale-West Palm Beach from 33 to 22; Los Angeles-Long Beach-Anaheim from 7 to 2. More affordable: St. Louis from 223 to 307; Minneapolis-St. Paul-Bloomington from 114 to 195; Washington-Arlington-Alexandria from 25 to 102. | rank correlation 0.94; 17 of the 20 largest metros move beyond their intervals; largest move Lexington Park, MD, 72 to 243 |
| Who still buys | The buyer is richer than in 2019 by +0.15 of the local median income (interval +0.12 to +0.19) and, against the claim, slightly younger: the under 35 share rose +1.2 pts (interval +0.1 pts to +2.3 pts) by 2025. The ratio moved most in Los Angeles-Long Beach-Anaheim +0.44; Miami-Fort Lauderdale-West Palm Beach +0.37; New York-Newark-Jersey City +0.30. | borrower income over the local median 1.23x to 1.39x (+0.15, +0.12 to +0.19); under 35 share +1.2 pts |
| The migration shock | The metros that gained people were already lagging before the pandemic: the placebo on the years before it is -0.8% (interval -1.4% to -0.2%), so the headline of +1.5% price growth over the window per person gained per hundred residents beyond the pre pandemic pace is a lower bound on what the migration itself did. | +1.48% per person gained per hundred residents (+0.40% to +2.55%); placebo -0.78% (-1.35% to -0.20%) |
| The reader decision | Buying beats renting only after 10.0 years in the typical metro (interval 1.0 years to beyond 30 years), and one point of rate moves the breakeven by +4.5 years. Longest to break even among the largest metros: Boston-Cambridge-Newton 21 years; Chicago-Naperville-Elgin 20 years; San Francisco-Oakland-Fremont 18 years. | median breakeven 10.0 years (1.0 years to beyond 30 years); the median household can afford the median home in 221 of 382 metros |

Every chapter is a claim that could have come out the other way: a plan hashed before the estimate touched a real metro, an estimator first proven on a simulated country where the answer is known, a result with an interval, one chart with one message and the SQL behind it, a method note, and a paragraph on what a housing economist would push back on.

## What is in it

- **A modeled warehouse.** dbt over DuckDB: 35 models and 164 tests over prices, incomes, rents, rates, permits, population, loans and the delineation crosswalk, with 27 named quarantine rules that flag and count and delete nothing, and a metric layer that defines each of 21 metrics once, two ways, reconciled at 4 grains with 0 disagreements.
- **A simulator with known truth.** 60 synthetic metros over 20 years with known incomes and income distributions, known supply elasticities, known demand shocks with a reverse causality knob, a known rate path, owners with known mortgage rates and a known lock in response, planted self report bias and suppressed cells, and a true affordability ranking confounded by design. The recovery study ran 24 conditions with 20 seeds each, 8,160 grades over 17 estimators, and the chapter that fails under one condition says so.
- **The level is a stated decision.** The regulator publishes the movement of prices and the census publishes their level; every dollar here is the census median value in 2019 moved by the index, with the sensitivity to anchoring in 2015, 2017, 2019 and 2023 on the data page.
- **The reader tools.** An affordability calculator on a live API with a check log scored when the next quarter publishes, an explorer with the SQL behind every chart and an SQL box over the marts in the browser, a workbook with live formulas, Tableau and Power BI companions.

## Skills

| Skill | Where it lives |
|---|---|
| SQL | `warehouse/`, `metrics/`, the SQL behind every chart |
| Data modeling, analytics engineering | `warehouse/` (dbt models, tests, exposures) |
| Data quality | the quarantine rules (`packages/contracts`) and the report on the data page; the HMDA contract with its rounding rules |
| Geography and crosswalks | `data/delineations`, `docs/geography.md`, the vintage tests |
| Metric definitions and governance | `metrics/metrics.yml`, `docs/definitions.md` |
| Statistics: inference | `packages/stats` (block bootstrap, cluster robust errors, Monte Carlo over margins of error) |
| Statistics: multiple comparisons | Benjamini-Hochberg in every family (`packages/stats/multiple.py`) |
| Panel regression with fixed effects | The rate shock and the lock in, Where builders kept pace, prices rose less, The migration shock (`packages/stats/fe.py`, weighted cells) |
| Quasi experiments | The rate shock and the lock in and The migration shock (placebos, synthetic control with permutation inference) |
| Changepoint detection | The rent burden is a distribution problem (PELT) |
| Simulation and estimator validation | `packages/sim`, the recovery study (`packages/evaluation`) |
| Financial modeling | `packages/finance` (tested to the cent), the workbook model sheet |
| Probability for decisions | The reader decision, the breakeven intervals |
| Data storytelling | `story/`, the sticky chart layout, the method notes |
| Dashboards and BI | `exports/tableau`, `exports/powerbi`, `/explore` |
| Spreadsheet modeling | `exports/workbook.xlsx` with live formulas |
| APIs and persistence | `packages/api`, `fly.toml`, `scripts/check_persistence.py` |
| Visualization | `web/`, the validated palette, one message per chart |
| Communication | `report/briefing.md`, the pushback paragraphs |
| Reproducibility | the claim gate, the rederive, the corrections log |
| Data licensing and provenance | `data/PROVENANCE.md`, the declared sources |

## Definition of done

1. **done.** Every source ingested for the whole window from the fetched files, the quarantine report published, the delineation crosswalk tested, the HMDA extract filter and the ACS gap stated in the README first paragraph, provenance and licenses recorded. *Evidence:* FHFA 85,272 index rows to 2026Q2; ACS 2,415,786 estimates over 19 releases (2005 to 2024, gap 2020); HMDA 55,817,457 loans in the analysis from 137,678,531 source rows (2018 to 2025); 7 delineation vintages; 27 quarantine rules on the data page; data/PROVENANCE.md.
2. **done.** Warehouse with dbt tests and exposures; the metric layer reconciled across grains. *Evidence:* dbt build: 35 models, 164 tests, 0 failed; 21 metrics reconciled at 4 grains over 1,764 cells with 0 disagreements.
3. **done.** Simulator with known incomes, distributions, elasticities, demand shocks, rates, lock in and planted misreporting; the recovery study on every condition with at least twenty seeds; the finance engine tested to the cent. *Evidence:* 60 simulated metros over 20 years; 24 conditions times 20 seeds, 8,160 grades across 17 estimators; finance tests 22 passed (0 failed); results/recovery.
4. **done.** Chapters 1 and 2 with plan hashes, simulator recovery, results on the test years with intervals, the anchor sensitivity table, the overtaking quarter named, the lock in regression with its placebo. *Evidence:* plans ac7975b9fb0c601f and dc55265cae0a0e21; payment share +1.1 pts against the peak (+1.0 pts to +1.3 pts); anchor sensitivity table ch1.anchor_sensitivity (stable); overtaking quarter 2023Q3; lock in -0.056 (-0.077 to -0.034) against a placebo of +0.001.
5. **done.** Chapter 3: the burden shares by metro, year and income bracket with intervals; the changepoints named. *Evidence:* plan a2850a134d98e2a1; burdened 52.5% (51.5% to 53.5%), severe 26.5% (25.7% to 27.2%) over 392 metros; by income group in ch3.by_income_group; changepoints 2009, 2015, 2021.
6. **done.** Chapter 5: the fair ranking with Monte Carlo intervals beside the raw ranking, the rank changes named, the simulator recovery. *Evidence:* plan e23fc6df73f96272; 382 metros ranked with 10,000 draws; rank correlation 0.94, 17 of the 20 largest move beyond their intervals; simulator rank correlation 0.956 adjusted against 0.890 raw.
7. **not done.** API deployed on Fly with Neon; live URL in the README; verified from a separate client, with the client response printed. *Evidence:* not yet deployed; results/deploy/verification.json is not written until a host holds the container.
8. **done.** Checks and scores observed from an independent connection; audit before response; the out of process check. *Evidence:* tests/api: 8 passed (test_check_is_committed, test_score_is_committed, test_audit_precedes_response, the out of process scripts/check_persistence.py).
9. **done.** Chapter 4: the supply elasticity under both specifications with intervals and the recovery study beside it; chapter 7: the migration regression with its placebo and three synthetic controls with placebo inference. *Evidence:* supply -8.0% per window with the demand control (-14.3% to -1.7%), -0.4% without; simulator bias +0.0026 against +0.0058; migration +1.48% (+0.40% to +2.55%) with placebo -0.78%; 3 synthetic controls with permutation p values.
10. **done.** Chapter 6: the borrower pool measures by year and metro with intervals. *Evidence:* plan 5714fb93ae481cb1; borrower ratio 1.23x to 1.39x (+0.15, +0.12 to +0.19); under 35 share moved +1.2 pts; by year in ch6.by_year and by metro in ch6.largest_metros.
11. **done.** Chapter 8: the affordable price by decile, the affordable share, the down payment years, the breakeven horizons with intervals, every interior test. *Evidence:* plan 10988e362f89ee23; median breakeven 10.0 years (1.0 years to beyond 30 years); the median household can afford the median home in 221 of 382 metros; down payment years 6.4 years; interior tests: line degenerate, down payment stable.
12. **done.** Exports: the workbook with live formulas and its recalculation test, the Tableau extract and specification, the Power BI specification with measures, the CSV bundle with its dictionary. *Evidence:* workbook 26 sheets, 1,816 live formulas, recalculation test passed; 5 Tableau views; 10 DAX measures; 25 CSV files with a dictionary.
13. **not done.** The story live on GitHub Pages with sticky charts, method notes, the SQL behind every chart, the corrections section and the print stylesheet. *Evidence:* not yet published: live check not checked.
14. **not done.** Explore, rank, buyers, shocks, planner, data and report pages live, working from the recorded session when the API is asleep; the test server refuses what the host refuses. *Evidence:* 0 of 0 routes loaded live; asleep: not observed; Playwright against the test server: 29 passed, 0 failed.
15. **not done.** Latency published; the live check in a real browser recorded in results/live_check.json. *Evidence:* POST /v1/checks p50 not measured, p99 not measured; results/live_check.json not checked.
16. **not done.** RESULTS.md with every figure re-derived by the gate and a specific limitations section. *Evidence:* claim gate over every document; rederive drift not run; limitations section in RESULTS.md.
17. **done.** README with the matrix and this checklist; DECISIONS.md with at least ten dated entries, two reversals and the corrections; three executed notebooks with a dead end each; the pushback paragraph on every chapter and page. *Evidence:* DECISIONS.md 20 dated entries, 2 reversals, 0 corrections; 3 executed notebooks, 3 with a dead end.
18. **not done.** Coverage at or above 80 percent, mypy strict clean, ruff clean, zero em dashes, zero banned vocabulary, palette validator green including the dark card run, forty to sixty commits, the rederive run in a worktree before the tag, v0.1.0 pushed after the commits, Apache 2.0 for code with every data source terms declared, repo described, topics set. *Evidence:* coverage 86.0 percent; mypy clean; ruff clean; palette green; 48 commits; rederive not run; tag not pushed; Apache 2.0 with every data source's terms declared.

Stretch, not counted: wages as a second income measure (not done), the vendor cross check (not done), the county view (not done), the owners chapter (not done), household formation (not done), the containers in CI (not done).

## Run it

```
make setup        # uv sync and the site's packages
make data         # every source into typed, flagged parquet; the crosswalk; the HMDA extract
make warehouse    # dbt build and test, then the shipped marts
make metrics      # the metric layer's reconcile
make simulate     # the demonstration country and its truth
make recovery     # every estimator on every condition and seed
make chapters     # plans registered, then the eight chapters and the calculator marts
make exports manifest render marts
make gates        # dash, vocabulary, statement, claim gate, identifier scan, palette
make test         # with the Postgres tests when DOORSTEP_TEST_DATABASE_URL is set
make rederive     # everything again from the raw files in a worktree, and a diff
```

The raw files are fetched on a machine that can reach the hosts (`deploy/fetch-data.ps1`, with a free Census API key); `docs/runbook.md` has the order, what each step writes and what to do when one stops.

## How this was built

Built with Claude as a pair programmer, over one long working session. The design, the scope and every call about method and trade off are mine; Claude wrote most of the implementation and the tests, and the commit history is left as it happened, trailers included. `DECISIONS.md` records what was challenged along the way and what changed because of it, including the two reversals the simulator forced and the two defects the warehouse tests caught in the first real build.

## Data and licenses

Code: Apache 2.0. Data: the Federal Housing Finance Agency house price index, the Census Bureau's American Community Survey, Building Permits Survey, population estimates and delineation files, the Department of Housing and Urban Development's fair market rents and income limits and the Consumer Financial Protection Bureau's mortgage disclosure extract are U.S. government works in the public domain; the Freddie Mac Primary Mortgage Market Survey is free with attribution under its terms of use, attributed in `data/PROVENANCE.md` and on every page that shows a rate. `data/PROVENANCE.md` lists every file with its source and its checksum. The derived race and ethnicity fields of the loan extract are not loaded. This is a portfolio analysis and a demonstration API with a token gate on writes and no other authentication; it is not financial advice, not a forecast and not a fair lending finding.
