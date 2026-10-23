# Methods

> Public data from the Federal Housing Finance Agency, the Census Bureau (American Community Survey, Building Permits Survey, Population Estimates), the Department of Housing and Urban Development and the Consumer Financial Protection Bureau (HMDA), with mortgage rates from Freddie Mac under its terms of use. Metros are real and appear as they do in the public record; no household, borrower or address appears. The findings are a portfolio analysis, not financial advice, not a market forecast and not a fair lending finding.

## Pre registration

Each chapter module exposes `plan()`: the claim, the estimator, the split, the family of comparisons and the interval method, as a dictionary hashed with SHA-256 over its canonical JSON. `doorstep chapters` registers every hash in `results/chapters/plans.json` before any estimate runs on real metros; a plan whose hash differs from its registration fails the run (`doorstep_chapters.plans.RegistrationError`), and a chapter that reports on its fitting years is rejected (`SplitViolation`). The hashes: chapter 1 `ac7975b9fb0c601f`, chapter 2 `dc55265cae0a0e21`, chapter 3 `a2850a134d98e2a1`, chapter 4 `a1d050c1b22c5986`, chapter 5 `e23fc6df73f96272`, chapter 6 `5714fb93ae481cb1`, chapter 7 `b2cbe5f6a4559c90`, chapter 8 `10988e362f89ee23`.

## The split

Chapters that fit anything choose on 2005 to 2019 and report on 2021 onward; descriptive chapters report the latest release. The lock in regression's base years are 2018 and 2019 and its test years start in 2023; the migration window is 2019Q4 to 2021Q4 with the placebo on 2016Q4 to 2018Q4.

## Intervals

- **Monte Carlo over the census margins** (chapters 1 and 5): each ACS estimate is drawn from a normal with standard deviation margin over 2,000 draws, the index held fixed, and the statistic is recomputed per draw; the interval is the percentile interval at 95%. Code: `doorstep_stats.monte_carlo`.
- **Block bootstrap** (chapters 3, 6 and 8): resampling metros, lenders or blocks of years with replacement, 400 replicates in the full run. Code: `doorstep_stats.bootstrap`.
- **Cluster robust regression** (chapters 2, 4 and 7): weighted least squares with the fixed effects absorbed by alternating projections on weighted cells (`doorstep_stats.fe`, which reproduces a row level fit on a fixture to floating tolerance), CR1 standard errors clustered by state, and intervals on the t distribution with one fewer degree of freedom than there are clusters. Code: `doorstep_stats.regression`.
- **Synthetic control** (chapter 7): weights on the simplex found by sequential least squares over every donor whose shock was small, with each donor treated in turn as a placebo; the p value is the rank of the treated metro's mean post gap among the placebos. Code: `doorstep_stats.synthetic`.
- **Changepoints** (chapter 3): PELT with a BIC penalty and a minimum segment of three years on the national severely burdened series. Code: `doorstep_stats.pelt`.
- **Benjamini-Hochberg** at q = 0.05 wherever a chapter publishes a family of comparisons (`doorstep_stats.multiple`); the chapters whose family is one comparison say so in their method note.

## Interior tests

Every operating point prints its headline under its neighbours and the word degenerate when the headline turns at the first one: the affordable line over 25%, 28%, 30% and 35% (degenerate in chapter 8), the down payment over 5%, 10% and 20% (stable), the saving rate over 5%, 10% and 15%, the anchor year over 2015, 2017, 2019 and 2023 (stable), the lock in threshold over 3.0%, 3.5% and 4.0% (stable), the supply window over 3, 5 and 7 years (degenerate) and the severe line over 15%, 20% and 25% (stable).

## The recovery study

`doorstep recovery` generates 24 conditions (demand strength at two levels, supply dispersion at two, reverse causality at three, noise at two) with 20 seeds each, runs every chapter's `simulate_estimate` on each world and grades it against the planted truth: 8,160 grades over 17 estimators, cached by a digest of the simulator and chapter sources. The worst grade is migration_naive under strong_demand/narrow_supply/strong_reverse/low_noise. The study is the only place an estimator is told it is wrong: real metros have no truth to grade against.

| Estimator | Mean bias | Mean RMSE | Mean coverage | Mean flag rate | Worst bias under | Lowest coverage | Lowest coverage under |
|---|---:|---:|---:|---:|---|---:|---|
| anchored_level | -0.0014 | 0.0135 | not applicable | not applicable | weak_demand/narrow_supply/none_reverse/high_noise | not applicable | not available |
| anchored_payment_share | -0.0002 | 0.0038 | 43% | not applicable | weak_demand/narrow_supply/none_reverse/low_noise | 35% | weak_demand/narrow_supply/mild_reverse/high_noise |
| borrower_ratio_shift | -0.0011 | 0.0058 | 76% | not applicable | strong_demand/narrow_supply/strong_reverse/high_noise | 55% | weak_demand/wide_supply/mild_reverse/low_noise |
| bracket_interpolation | +0.0037 | 0.0039 | not applicable | not applicable | weak_demand/narrow_supply/strong_reverse/high_noise | not applicable | not available |
| breakeven_horizon | +4.4168 | 4.4415 | not applicable | 70% | weak_demand/narrow_supply/strong_reverse/low_noise | not applicable | not available |
| burden_changepoint | +0.0042 | 0.0186 | not applicable | 100% | strong_demand/narrow_supply/strong_reverse/low_noise | not applicable | not available |
| lock_in_did | +0.0015 | 0.0055 | 94% | 85% | weak_demand/narrow_supply/none_reverse/high_noise | 85% | weak_demand/narrow_supply/strong_reverse/high_noise |
| lock_in_placebo | -0.0001 | 0.0087 | 85% | not applicable | strong_demand/narrow_supply/none_reverse/high_noise | 80% | strong_demand/narrow_supply/mild_reverse/high_noise |
| migration_effect | -0.0002 | 0.0027 | 98% | 18% | strong_demand/wide_supply/strong_reverse/low_noise | 95% | strong_demand/narrow_supply/none_reverse/low_noise |
| migration_naive | -0.0036 | 0.0043 | 61% | not applicable | strong_demand/wide_supply/strong_reverse/low_noise | 5% | strong_demand/narrow_supply/strong_reverse/low_noise |
| migration_placebo | -0.0027 | 0.0043 | 82% | not applicable | strong_demand/wide_supply/strong_reverse/high_noise | 15% | strong_demand/narrow_supply/strong_reverse/high_noise |
| ranking_adjusted | -0.0437 | 0.0475 | not applicable | 89% | strong_demand/narrow_supply/strong_reverse/low_noise | not applicable | not available |
| self_report_correction | -0.0015 | 0.0034 | not applicable | 2% | weak_demand/wide_supply/mild_reverse/low_noise | not applicable | not available |
| severe_share | 0.0000 | 0.0000 | 100% | not applicable | strong_demand/narrow_supply/none_reverse/low_noise | 100% | strong_demand/narrow_supply/mild_reverse/high_noise |
| supply_controlled | +0.0026 | 0.0043 | 85% | not applicable | strong_demand/narrow_supply/strong_reverse/high_noise | 70% | strong_demand/wide_supply/strong_reverse/high_noise |
| supply_uncontrolled | +0.0058 | 0.0070 | 70% | not applicable | strong_demand/narrow_supply/strong_reverse/high_noise | 30% | strong_demand/narrow_supply/strong_reverse/high_noise |
| under_35_shift | -0.0002 | 0.0018 | 85% | not applicable | strong_demand/wide_supply/mild_reverse/high_noise | 60% | strong_demand/wide_supply/mild_reverse/high_noise |

## Determinism

Every seeded step sorts before it samples and seeds its generator from the policy seed (20261022) and a label; every published table has a stable tie break; the manifest is identical under two PYTHONHASHSEED values; caches are keyed by a digest of their inputs and a changed input is a miss.
