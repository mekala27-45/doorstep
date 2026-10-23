# Results

Every figure on this page is rendered from `results/manifest.json` (as of 2026-10-23) by the claim gate, which re-renders the page in CI and fails on any difference. Prices and rates run from 2000 to 2026Q2, the census releases from 2005 to 2024 with 2020 carried as a gap, and the loan extract from 2018 to 2025. Chapters that fit anything choose on 2005 to 2019 and report from 2021.

> Public data from the Federal Housing Finance Agency, the Census Bureau (American Community Survey, Building Permits Survey, Population Estimates), the Department of Housing and Urban Development and the Consumer Financial Protection Bureau (HMDA), with mortgage rates from Freddie Mac under its terms of use. Metros are real and appear as they do in the public record; no household, borrower or address appears. The findings are a portfolio analysis, not financial advice, not a market forecast and not a fair lending finding.

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

12 of 18 done; not done: 7, 13, 14, 15, 16, 18.

Stretch items, not counted toward the checklist: wages as a second income measure, the vendor cross check, the county view, the owners chapter, household formation and the containers built in CI are not done in this release.

## The eight chapters

| Chapter | Plan hash | The finding | Headline with interval |
|---|---|---|---|
| Affordable is a decision | `ac7975b9fb0c601f` | The payment share of 2024 does not exceed 2023; the payment story is not yet the largest the window has seen. It sits +1.1 pts above 2006 (interval +1.0 pts to +1.3 pts), so the 2006 peak is passed, and the window's own peak is 2023. | payment share 34.9% (34.8% to 35.0%); +1.1 pts against 2006 (+1.0 pts to +1.3 pts) |
| The rate shock and the lock in | `dc55265cae0a0e21` | The rate part of the payment overtook the price part in 2023Q3. The rate shock froze turnover where owners had the most to lose: 0.06 fewer purchases per 100 owner households per point of lock in (interval -0.08 to -0.03), and the placebo on the years before the shock sits at 0.00 with an interval that includes zero. | rate part +$549 of +$1,388; lock in -0.056 (-0.077 to -0.034); placebo +0.001 (-0.002 to +0.004) |
| The rent burden is a distribution problem | `a2850a134d98e2a1` | The median renter is burdened in 51% of metros in 2024, so the median hides nothing; the problem is the whole distribution, with 26.5% of renters paying half or more (interval 25.7% to 27.2%). The national series moved and stayed moved in 2009, 2015, 2021. | burdened 52.5% (51.5% to 53.5%); severe 26.5% (25.7% to 27.2%) |
| Where builders kept pace, prices rose less | `a1d050c1b22c5986` | Where builders kept pace, prices rose less: 8.0% less price growth over 5 years per extra permit per hundred households (interval -14.3% to -1.7%); without the demand control the estimate is -0.4%. | controlled -0.0160 (-0.0286 to -0.0034); uncontrolled -0.0009 (-0.0092 to +0.0074) per permit per hundred households per year |
| The fair ranking | `e23fc6df73f96272` | The ranking changes when you hold constant what people earn there: 17 of the 20 largest metros move beyond their intervals. Less affordable than their price says: Tampa-St. Petersburg-Clearwater from 106 to 90; Miami-Fort Lauderdale-West Palm Beach from 33 to 22; Los Angeles-Long Beach-Anaheim from 7 to 2. More affordable: St. Louis from 223 to 307; Minneapolis-St. Paul-Bloomington from 114 to 195; Washington-Arlington-Alexandria from 25 to 102. | least affordable Kahului-Wailuku, HI at 75.5% (69.7% to 81.7%); rank correlation 0.94 |
| Who still buys | `5714fb93ae481cb1` | The buyer is richer than in 2019 by +0.15 of the local median income (interval +0.12 to +0.19) and, against the claim, slightly younger: the under 35 share rose +1.2 pts (interval +0.1 pts to +2.3 pts) by 2025. The ratio moved most in Los Angeles-Long Beach-Anaheim +0.44; Miami-Fort Lauderdale-West Palm Beach +0.37; New York-Newark-Jersey City +0.30. | ratio shift +0.15 (+0.12 to +0.19); under 35 shift +1.2 pts (+0.1 pts to +2.3 pts) |
| The migration shock | `b2cbe5f6a4559c90` | The metros that gained people were already lagging before the pandemic: the placebo on the years before it is -0.8% (interval -1.4% to -0.2%), so the headline of +1.5% price growth over the window per person gained per hundred residents beyond the pre pandemic pace is a lower bound on what the migration itself did. | +1.48% (+0.40% to +2.55%); placebo -0.78% (-1.35% to -0.20%) |
| The reader decision | `10988e362f89ee23` | Buying beats renting only after 10.0 years in the typical metro (interval 1.0 years to beyond 30 years), and one point of rate moves the breakeven by +4.5 years. Longest to break even among the largest metros: Boston-Cambridge-Newton 21 years; Chicago-Naperville-Elgin 20 years; San Francisco-Oakland-Fremont 18 years. | median breakeven 10.0 years (1.0 years to beyond 30 years); one point of rate moves it +4.5 years |

## The recovery study

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

*Source: the simulated metros with known truth, the recovery study, every condition and seed, 20 seeds, as of 2026-10-22.*

The worst grade in the study is migration_naive under strong_demand/narrow_supply/strong_reverse/low_noise. The supply elasticity (planted at -0.025) comes back with a mean bias of +0.0026 with the demand control and +0.0058 without it, +0.0031 against +0.0078 under strong demand. The migration effect comes back with a mean bias of -0.02% and 98% coverage; the regression on the migration level alone carries -0.30% with no reverse causality and -0.51% under strong reverse causality, and the placebo flags that condition in 46% of worlds against 6% under none. The lock in difference in differences has a mean bias of +0.0015 with 94% coverage. The adjusted ranking's rank correlation with the truth is 0.956 against 0.890 for the price ranking. The breakeven, graded as late arriving truth, misses the realised year by 4.42 years on average, because the simulated decade after the estimate held a boom the history did not.

| Estimator | Condition | Seeds | Bias | RMSE | Coverage | Flag rate |
|---|---|---:|---:|---:|---:|---:|
| anchored_level | strong_demand/narrow_supply/mild_reverse/high_noise | 20 | +0.0003 | 0.0109 | not applicable | not applicable |
| anchored_level | strong_demand/narrow_supply/mild_reverse/low_noise | 20 | +0.0001 | 0.0110 | not applicable | not applicable |
| anchored_level | strong_demand/narrow_supply/none_reverse/high_noise | 20 | +0.0004 | 0.0125 | not applicable | not applicable |
| anchored_level | strong_demand/narrow_supply/none_reverse/low_noise | 20 | +0.0003 | 0.0125 | not applicable | not applicable |
| anchored_level | strong_demand/narrow_supply/strong_reverse/high_noise | 20 | +0.0001 | 0.0097 | not applicable | not applicable |
| anchored_level | strong_demand/narrow_supply/strong_reverse/low_noise | 20 | -0.0001 | 0.0096 | not applicable | not applicable |
| anchored_level | strong_demand/wide_supply/mild_reverse/high_noise | 20 | +0.0004 | 0.0109 | not applicable | not applicable |
| anchored_level | strong_demand/wide_supply/mild_reverse/low_noise | 20 | +0.0002 | 0.0110 | not applicable | not applicable |
| anchored_level | strong_demand/wide_supply/none_reverse/high_noise | 20 | +0.0005 | 0.0126 | not applicable | not applicable |
| anchored_level | strong_demand/wide_supply/none_reverse/low_noise | 20 | +0.0004 | 0.0126 | not applicable | not applicable |
| anchored_level | strong_demand/wide_supply/strong_reverse/high_noise | 20 | +0.0001 | 0.0096 | not applicable | not applicable |
| anchored_level | strong_demand/wide_supply/strong_reverse/low_noise | 20 | 0.0000 | 0.0096 | not applicable | not applicable |
| anchored_level | weak_demand/narrow_supply/mild_reverse/high_noise | 20 | -0.0032 | 0.0159 | not applicable | not applicable |
| anchored_level | weak_demand/narrow_supply/mild_reverse/low_noise | 20 | -0.0031 | 0.0160 | not applicable | not applicable |
| anchored_level | weak_demand/narrow_supply/none_reverse/high_noise | 20 | -0.0032 | 0.0159 | not applicable | not applicable |
| anchored_level | weak_demand/narrow_supply/none_reverse/low_noise | 20 | -0.0031 | 0.0160 | not applicable | not applicable |
| anchored_level | weak_demand/narrow_supply/strong_reverse/high_noise | 20 | -0.0030 | 0.0159 | not applicable | not applicable |
| anchored_level | weak_demand/narrow_supply/strong_reverse/low_noise | 20 | -0.0029 | 0.0160 | not applicable | not applicable |
| anchored_level | weak_demand/wide_supply/mild_reverse/high_noise | 20 | -0.0032 | 0.0160 | not applicable | not applicable |
| anchored_level | weak_demand/wide_supply/mild_reverse/low_noise | 20 | -0.0031 | 0.0160 | not applicable | not applicable |
| anchored_level | weak_demand/wide_supply/none_reverse/high_noise | 20 | -0.0031 | 0.0159 | not applicable | not applicable |
| anchored_level | weak_demand/wide_supply/none_reverse/low_noise | 20 | -0.0031 | 0.0159 | not applicable | not applicable |
| anchored_level | weak_demand/wide_supply/strong_reverse/high_noise | 20 | -0.0030 | 0.0161 | not applicable | not applicable |
| anchored_level | weak_demand/wide_supply/strong_reverse/low_noise | 20 | -0.0030 | 0.0162 | not applicable | not applicable |
| anchored_payment_share | strong_demand/narrow_supply/mild_reverse/high_noise | 20 | +0.0003 | 0.0030 | 50% | not applicable |
| anchored_payment_share | strong_demand/narrow_supply/mild_reverse/low_noise | 20 | +0.0003 | 0.0030 | 45% | not applicable |
| anchored_payment_share | strong_demand/narrow_supply/none_reverse/high_noise | 20 | +0.0004 | 0.0036 | 50% | not applicable |
| anchored_payment_share | strong_demand/narrow_supply/none_reverse/low_noise | 20 | +0.0004 | 0.0036 | 50% | not applicable |
| anchored_payment_share | strong_demand/narrow_supply/strong_reverse/high_noise | 20 | +0.0002 | 0.0025 | 50% | not applicable |
| anchored_payment_share | strong_demand/narrow_supply/strong_reverse/low_noise | 20 | +0.0001 | 0.0025 | 50% | not applicable |
| anchored_payment_share | strong_demand/wide_supply/mild_reverse/high_noise | 20 | +0.0003 | 0.0030 | 50% | not applicable |
| anchored_payment_share | strong_demand/wide_supply/mild_reverse/low_noise | 20 | +0.0003 | 0.0030 | 45% | not applicable |
| anchored_payment_share | strong_demand/wide_supply/none_reverse/high_noise | 20 | +0.0004 | 0.0036 | 50% | not applicable |
| anchored_payment_share | strong_demand/wide_supply/none_reverse/low_noise | 20 | +0.0004 | 0.0037 | 50% | not applicable |
| anchored_payment_share | strong_demand/wide_supply/strong_reverse/high_noise | 20 | +0.0002 | 0.0025 | 50% | not applicable |
| anchored_payment_share | strong_demand/wide_supply/strong_reverse/low_noise | 20 | +0.0002 | 0.0025 | 50% | not applicable |
| anchored_payment_share | weak_demand/narrow_supply/mild_reverse/high_noise | 20 | -0.0006 | 0.0045 | 35% | not applicable |
| anchored_payment_share | weak_demand/narrow_supply/mild_reverse/low_noise | 20 | -0.0007 | 0.0045 | 35% | not applicable |
| anchored_payment_share | weak_demand/narrow_supply/none_reverse/high_noise | 20 | -0.0007 | 0.0046 | 35% | not applicable |
| anchored_payment_share | weak_demand/narrow_supply/none_reverse/low_noise | 20 | -0.0007 | 0.0046 | 35% | not applicable |
| anchored_payment_share | weak_demand/narrow_supply/strong_reverse/high_noise | 20 | -0.0006 | 0.0043 | 50% | not applicable |
| anchored_payment_share | weak_demand/narrow_supply/strong_reverse/low_noise | 20 | -0.0006 | 0.0043 | 40% | not applicable |
| anchored_payment_share | weak_demand/wide_supply/mild_reverse/high_noise | 20 | -0.0006 | 0.0046 | 35% | not applicable |
| anchored_payment_share | weak_demand/wide_supply/mild_reverse/low_noise | 20 | -0.0006 | 0.0046 | 35% | not applicable |
| anchored_payment_share | weak_demand/wide_supply/none_reverse/high_noise | 20 | -0.0006 | 0.0046 | 35% | not applicable |
| anchored_payment_share | weak_demand/wide_supply/none_reverse/low_noise | 20 | -0.0007 | 0.0046 | 35% | not applicable |
| anchored_payment_share | weak_demand/wide_supply/strong_reverse/high_noise | 20 | -0.0005 | 0.0043 | 45% | not applicable |
| anchored_payment_share | weak_demand/wide_supply/strong_reverse/low_noise | 20 | -0.0006 | 0.0043 | 35% | not applicable |
| borrower_ratio_shift | strong_demand/narrow_supply/mild_reverse/high_noise | 20 | -0.0022 | 0.0056 | 80% | not applicable |
| borrower_ratio_shift | strong_demand/narrow_supply/mild_reverse/low_noise | 20 | -0.0022 | 0.0065 | 70% | not applicable |
| borrower_ratio_shift | strong_demand/narrow_supply/none_reverse/high_noise | 20 | -0.0008 | 0.0060 | 85% | not applicable |
| borrower_ratio_shift | strong_demand/narrow_supply/none_reverse/low_noise | 20 | -0.0008 | 0.0060 | 85% | not applicable |
| borrower_ratio_shift | strong_demand/narrow_supply/strong_reverse/high_noise | 20 | -0.0023 | 0.0058 | 60% | not applicable |
| borrower_ratio_shift | strong_demand/narrow_supply/strong_reverse/low_noise | 20 | -0.0013 | 0.0054 | 70% | not applicable |
| borrower_ratio_shift | strong_demand/wide_supply/mild_reverse/high_noise | 20 | -0.0017 | 0.0051 | 80% | not applicable |
| borrower_ratio_shift | strong_demand/wide_supply/mild_reverse/low_noise | 20 | -0.0019 | 0.0064 | 70% | not applicable |
| borrower_ratio_shift | strong_demand/wide_supply/none_reverse/high_noise | 20 | -0.0008 | 0.0060 | 85% | not applicable |
| borrower_ratio_shift | strong_demand/wide_supply/none_reverse/low_noise | 20 | -0.0008 | 0.0060 | 85% | not applicable |
| borrower_ratio_shift | strong_demand/wide_supply/strong_reverse/high_noise | 20 | -0.0017 | 0.0065 | 80% | not applicable |
| borrower_ratio_shift | strong_demand/wide_supply/strong_reverse/low_noise | 20 | -0.0019 | 0.0050 | 75% | not applicable |
| borrower_ratio_shift | weak_demand/narrow_supply/mild_reverse/high_noise | 20 | -0.0017 | 0.0060 | 70% | not applicable |
| borrower_ratio_shift | weak_demand/narrow_supply/mild_reverse/low_noise | 20 | -0.0012 | 0.0051 | 70% | not applicable |
| borrower_ratio_shift | weak_demand/narrow_supply/none_reverse/high_noise | 20 | -0.0014 | 0.0049 | 85% | not applicable |
| borrower_ratio_shift | weak_demand/narrow_supply/none_reverse/low_noise | 20 | -0.0014 | 0.0049 | 85% | not applicable |
| borrower_ratio_shift | weak_demand/narrow_supply/strong_reverse/high_noise | 20 | +0.0018 | 0.0070 | 70% | not applicable |
| borrower_ratio_shift | weak_demand/narrow_supply/strong_reverse/low_noise | 20 | +0.0006 | 0.0060 | 70% | not applicable |
| borrower_ratio_shift | weak_demand/wide_supply/mild_reverse/high_noise | 20 | -0.0015 | 0.0062 | 75% | not applicable |
| borrower_ratio_shift | weak_demand/wide_supply/mild_reverse/low_noise | 20 | -0.0013 | 0.0062 | 55% | not applicable |
| borrower_ratio_shift | weak_demand/wide_supply/none_reverse/high_noise | 20 | -0.0014 | 0.0049 | 85% | not applicable |
| borrower_ratio_shift | weak_demand/wide_supply/none_reverse/low_noise | 20 | -0.0014 | 0.0049 | 85% | not applicable |
| borrower_ratio_shift | weak_demand/wide_supply/strong_reverse/high_noise | 20 | +0.0020 | 0.0061 | 70% | not applicable |
| borrower_ratio_shift | weak_demand/wide_supply/strong_reverse/low_noise | 20 | -0.0004 | 0.0058 | 70% | not applicable |
| bracket_interpolation | strong_demand/narrow_supply/mild_reverse/high_noise | 20 | +0.0036 | 0.0039 | not applicable | not applicable |
| bracket_interpolation | strong_demand/narrow_supply/mild_reverse/low_noise | 20 | +0.0035 | 0.0038 | not applicable | not applicable |
| bracket_interpolation | strong_demand/narrow_supply/none_reverse/high_noise | 20 | +0.0039 | 0.0042 | not applicable | not applicable |
| bracket_interpolation | strong_demand/narrow_supply/none_reverse/low_noise | 20 | +0.0038 | 0.0041 | not applicable | not applicable |
| bracket_interpolation | strong_demand/narrow_supply/strong_reverse/high_noise | 20 | +0.0027 | 0.0029 | not applicable | not applicable |
| bracket_interpolation | strong_demand/narrow_supply/strong_reverse/low_noise | 20 | +0.0025 | 0.0026 | not applicable | not applicable |
| bracket_interpolation | strong_demand/wide_supply/mild_reverse/high_noise | 20 | +0.0036 | 0.0039 | not applicable | not applicable |
| bracket_interpolation | strong_demand/wide_supply/mild_reverse/low_noise | 20 | +0.0034 | 0.0037 | not applicable | not applicable |
| bracket_interpolation | strong_demand/wide_supply/none_reverse/high_noise | 20 | +0.0039 | 0.0041 | not applicable | not applicable |
| bracket_interpolation | strong_demand/wide_supply/none_reverse/low_noise | 20 | +0.0037 | 0.0040 | not applicable | not applicable |
| bracket_interpolation | strong_demand/wide_supply/strong_reverse/high_noise | 20 | +0.0027 | 0.0029 | not applicable | not applicable |
| bracket_interpolation | strong_demand/wide_supply/strong_reverse/low_noise | 20 | +0.0025 | 0.0026 | not applicable | not applicable |
| bracket_interpolation | weak_demand/narrow_supply/mild_reverse/high_noise | 20 | +0.0040 | 0.0042 | not applicable | not applicable |
| bracket_interpolation | weak_demand/narrow_supply/mild_reverse/low_noise | 20 | +0.0040 | 0.0041 | not applicable | not applicable |
| bracket_interpolation | weak_demand/narrow_supply/none_reverse/high_noise | 20 | +0.0039 | 0.0041 | not applicable | not applicable |
| bracket_interpolation | weak_demand/narrow_supply/none_reverse/low_noise | 20 | +0.0039 | 0.0040 | not applicable | not applicable |
| bracket_interpolation | weak_demand/narrow_supply/strong_reverse/high_noise | 20 | +0.0044 | 0.0046 | not applicable | not applicable |
| bracket_interpolation | weak_demand/narrow_supply/strong_reverse/low_noise | 20 | +0.0044 | 0.0045 | not applicable | not applicable |
| bracket_interpolation | weak_demand/wide_supply/mild_reverse/high_noise | 20 | +0.0040 | 0.0042 | not applicable | not applicable |
| bracket_interpolation | weak_demand/wide_supply/mild_reverse/low_noise | 20 | +0.0040 | 0.0041 | not applicable | not applicable |
| bracket_interpolation | weak_demand/wide_supply/none_reverse/high_noise | 20 | +0.0039 | 0.0041 | not applicable | not applicable |
| bracket_interpolation | weak_demand/wide_supply/none_reverse/low_noise | 20 | +0.0039 | 0.0041 | not applicable | not applicable |
| bracket_interpolation | weak_demand/wide_supply/strong_reverse/high_noise | 20 | +0.0043 | 0.0045 | not applicable | not applicable |
| bracket_interpolation | weak_demand/wide_supply/strong_reverse/low_noise | 20 | +0.0043 | 0.0045 | not applicable | not applicable |
| breakeven_horizon | strong_demand/narrow_supply/mild_reverse/high_noise | 20 | +4.2426 | 4.2720 | not applicable | 72% |
| breakeven_horizon | strong_demand/narrow_supply/mild_reverse/low_noise | 20 | +4.2949 | 4.3268 | not applicable | 70% |
| breakeven_horizon | strong_demand/narrow_supply/none_reverse/high_noise | 20 | +4.3231 | 4.3555 | not applicable | 71% |
| breakeven_horizon | strong_demand/narrow_supply/none_reverse/low_noise | 20 | +4.4981 | 4.5312 | not applicable | 71% |
| breakeven_horizon | strong_demand/narrow_supply/strong_reverse/high_noise | 20 | +3.9630 | 3.9938 | not applicable | 71% |
| breakeven_horizon | strong_demand/narrow_supply/strong_reverse/low_noise | 20 | +3.8463 | 3.8817 | not applicable | 68% |
| breakeven_horizon | strong_demand/wide_supply/mild_reverse/high_noise | 20 | +4.2153 | 4.2439 | not applicable | 73% |
| breakeven_horizon | strong_demand/wide_supply/mild_reverse/low_noise | 20 | +4.2926 | 4.3260 | not applicable | 70% |
| breakeven_horizon | strong_demand/wide_supply/none_reverse/high_noise | 20 | +4.3093 | 4.3409 | not applicable | 72% |
| breakeven_horizon | strong_demand/wide_supply/none_reverse/low_noise | 20 | +4.4676 | 4.5007 | not applicable | 70% |
| breakeven_horizon | strong_demand/wide_supply/strong_reverse/high_noise | 20 | +3.8917 | 3.9252 | not applicable | 72% |
| breakeven_horizon | strong_demand/wide_supply/strong_reverse/low_noise | 20 | +3.7875 | 3.8233 | not applicable | 69% |
| breakeven_horizon | weak_demand/narrow_supply/mild_reverse/high_noise | 20 | +4.5824 | 4.6007 | not applicable | 68% |
| breakeven_horizon | weak_demand/narrow_supply/mild_reverse/low_noise | 20 | +4.7662 | 4.7825 | not applicable | 68% |
| breakeven_horizon | weak_demand/narrow_supply/none_reverse/high_noise | 20 | +4.5954 | 4.6128 | not applicable | 67% |
| breakeven_horizon | weak_demand/narrow_supply/none_reverse/low_noise | 20 | +4.7083 | 4.7281 | not applicable | 68% |
| breakeven_horizon | weak_demand/narrow_supply/strong_reverse/high_noise | 20 | +4.6009 | 4.6201 | not applicable | 69% |
| breakeven_horizon | weak_demand/narrow_supply/strong_reverse/low_noise | 20 | +4.7880 | 4.8033 | not applicable | 70% |
| breakeven_horizon | weak_demand/wide_supply/mild_reverse/high_noise | 20 | +4.5898 | 4.6069 | not applicable | 67% |
| breakeven_horizon | weak_demand/wide_supply/mild_reverse/low_noise | 20 | +4.7380 | 4.7530 | not applicable | 69% |
| breakeven_horizon | weak_demand/wide_supply/none_reverse/high_noise | 20 | +4.5949 | 4.6114 | not applicable | 68% |
| breakeven_horizon | weak_demand/wide_supply/none_reverse/low_noise | 20 | +4.6708 | 4.6870 | not applicable | 68% |
| breakeven_horizon | weak_demand/wide_supply/strong_reverse/high_noise | 20 | +4.5324 | 4.5506 | not applicable | 70% |
| breakeven_horizon | weak_demand/wide_supply/strong_reverse/low_noise | 20 | +4.7032 | 4.7195 | not applicable | 72% |
| burden_changepoint | strong_demand/narrow_supply/mild_reverse/high_noise | 20 | 0.0000 | 0.0000 | not applicable | 100% |
| burden_changepoint | strong_demand/narrow_supply/mild_reverse/low_noise | 20 | 0.0000 | 0.0000 | not applicable | 100% |
| burden_changepoint | strong_demand/narrow_supply/none_reverse/high_noise | 20 | 0.0000 | 0.0000 | not applicable | 100% |
| burden_changepoint | strong_demand/narrow_supply/none_reverse/low_noise | 20 | 0.0000 | 0.0000 | not applicable | 100% |
| burden_changepoint | strong_demand/narrow_supply/strong_reverse/high_noise | 20 | 0.0000 | 0.0000 | not applicable | 100% |
| burden_changepoint | strong_demand/narrow_supply/strong_reverse/low_noise | 20 | +0.0500 | 0.2236 | not applicable | 100% |
| burden_changepoint | strong_demand/wide_supply/mild_reverse/high_noise | 20 | 0.0000 | 0.0000 | not applicable | 100% |
| burden_changepoint | strong_demand/wide_supply/mild_reverse/low_noise | 20 | 0.0000 | 0.0000 | not applicable | 100% |
| burden_changepoint | strong_demand/wide_supply/none_reverse/high_noise | 20 | 0.0000 | 0.0000 | not applicable | 100% |
| burden_changepoint | strong_demand/wide_supply/none_reverse/low_noise | 20 | 0.0000 | 0.0000 | not applicable | 100% |
| burden_changepoint | strong_demand/wide_supply/strong_reverse/high_noise | 20 | 0.0000 | 0.0000 | not applicable | 100% |
| burden_changepoint | strong_demand/wide_supply/strong_reverse/low_noise | 20 | +0.0500 | 0.2236 | not applicable | 100% |
| burden_changepoint | weak_demand/narrow_supply/mild_reverse/high_noise | 20 | 0.0000 | 0.0000 | not applicable | 100% |
| burden_changepoint | weak_demand/narrow_supply/mild_reverse/low_noise | 20 | 0.0000 | 0.0000 | not applicable | 100% |
| burden_changepoint | weak_demand/narrow_supply/none_reverse/high_noise | 20 | 0.0000 | 0.0000 | not applicable | 100% |
| burden_changepoint | weak_demand/narrow_supply/none_reverse/low_noise | 20 | 0.0000 | 0.0000 | not applicable | 100% |
| burden_changepoint | weak_demand/narrow_supply/strong_reverse/high_noise | 20 | 0.0000 | 0.0000 | not applicable | 100% |
| burden_changepoint | weak_demand/narrow_supply/strong_reverse/low_noise | 20 | 0.0000 | 0.0000 | not applicable | 100% |
| burden_changepoint | weak_demand/wide_supply/mild_reverse/high_noise | 20 | 0.0000 | 0.0000 | not applicable | 100% |
| burden_changepoint | weak_demand/wide_supply/mild_reverse/low_noise | 20 | 0.0000 | 0.0000 | not applicable | 100% |
| burden_changepoint | weak_demand/wide_supply/none_reverse/high_noise | 20 | 0.0000 | 0.0000 | not applicable | 100% |
| burden_changepoint | weak_demand/wide_supply/none_reverse/low_noise | 20 | 0.0000 | 0.0000 | not applicable | 100% |
| burden_changepoint | weak_demand/wide_supply/strong_reverse/high_noise | 20 | 0.0000 | 0.0000 | not applicable | 100% |
| burden_changepoint | weak_demand/wide_supply/strong_reverse/low_noise | 20 | 0.0000 | 0.0000 | not applicable | 100% |
| lock_in_did | strong_demand/narrow_supply/mild_reverse/high_noise | 20 | +0.0005 | 0.0047 | 100% | 80% |
| lock_in_did | strong_demand/narrow_supply/mild_reverse/low_noise | 20 | +0.0005 | 0.0047 | 100% | 80% |
| lock_in_did | strong_demand/narrow_supply/none_reverse/high_noise | 20 | +0.0006 | 0.0049 | 100% | 80% |
| lock_in_did | strong_demand/narrow_supply/none_reverse/low_noise | 20 | +0.0006 | 0.0049 | 100% | 80% |
| lock_in_did | strong_demand/narrow_supply/strong_reverse/high_noise | 20 | +0.0004 | 0.0044 | 100% | 80% |
| lock_in_did | strong_demand/narrow_supply/strong_reverse/low_noise | 20 | +0.0004 | 0.0044 | 100% | 80% |
| lock_in_did | strong_demand/wide_supply/mild_reverse/high_noise | 20 | +0.0005 | 0.0047 | 100% | 80% |
| lock_in_did | strong_demand/wide_supply/mild_reverse/low_noise | 20 | +0.0005 | 0.0047 | 100% | 80% |
| lock_in_did | strong_demand/wide_supply/none_reverse/high_noise | 20 | +0.0006 | 0.0049 | 100% | 80% |
| lock_in_did | strong_demand/wide_supply/none_reverse/low_noise | 20 | +0.0006 | 0.0049 | 100% | 80% |
| lock_in_did | strong_demand/wide_supply/strong_reverse/high_noise | 20 | +0.0004 | 0.0044 | 100% | 80% |
| lock_in_did | strong_demand/wide_supply/strong_reverse/low_noise | 20 | +0.0004 | 0.0044 | 100% | 80% |
| lock_in_did | weak_demand/narrow_supply/mild_reverse/high_noise | 20 | +0.0025 | 0.0064 | 90% | 90% |
| lock_in_did | weak_demand/narrow_supply/mild_reverse/low_noise | 20 | +0.0026 | 0.0064 | 90% | 90% |
| lock_in_did | weak_demand/narrow_supply/none_reverse/high_noise | 20 | +0.0027 | 0.0064 | 90% | 90% |
| lock_in_did | weak_demand/narrow_supply/none_reverse/low_noise | 20 | +0.0027 | 0.0064 | 90% | 90% |
| lock_in_did | weak_demand/narrow_supply/strong_reverse/high_noise | 20 | +0.0022 | 0.0064 | 85% | 90% |
| lock_in_did | weak_demand/narrow_supply/strong_reverse/low_noise | 20 | +0.0023 | 0.0065 | 85% | 90% |
| lock_in_did | weak_demand/wide_supply/mild_reverse/high_noise | 20 | +0.0025 | 0.0064 | 90% | 90% |
| lock_in_did | weak_demand/wide_supply/mild_reverse/low_noise | 20 | +0.0026 | 0.0064 | 90% | 90% |
| lock_in_did | weak_demand/wide_supply/none_reverse/high_noise | 20 | +0.0027 | 0.0064 | 90% | 90% |
| lock_in_did | weak_demand/wide_supply/none_reverse/low_noise | 20 | +0.0027 | 0.0064 | 90% | 90% |
| lock_in_did | weak_demand/wide_supply/strong_reverse/high_noise | 20 | +0.0022 | 0.0064 | 85% | 90% |
| lock_in_did | weak_demand/wide_supply/strong_reverse/low_noise | 20 | +0.0023 | 0.0065 | 85% | 90% |
| lock_in_placebo | strong_demand/narrow_supply/mild_reverse/high_noise | 20 | -0.0015 | 0.0097 | 80% | not applicable |
| lock_in_placebo | strong_demand/narrow_supply/mild_reverse/low_noise | 20 | -0.0015 | 0.0097 | 80% | not applicable |
| lock_in_placebo | strong_demand/narrow_supply/none_reverse/high_noise | 20 | -0.0015 | 0.0098 | 80% | not applicable |
| lock_in_placebo | strong_demand/narrow_supply/none_reverse/low_noise | 20 | -0.0015 | 0.0098 | 80% | not applicable |
| lock_in_placebo | strong_demand/narrow_supply/strong_reverse/high_noise | 20 | -0.0013 | 0.0096 | 80% | not applicable |
| lock_in_placebo | strong_demand/narrow_supply/strong_reverse/low_noise | 20 | -0.0013 | 0.0097 | 80% | not applicable |
| lock_in_placebo | strong_demand/wide_supply/mild_reverse/high_noise | 20 | -0.0015 | 0.0097 | 80% | not applicable |
| lock_in_placebo | strong_demand/wide_supply/mild_reverse/low_noise | 20 | -0.0015 | 0.0097 | 80% | not applicable |
| lock_in_placebo | strong_demand/wide_supply/none_reverse/high_noise | 20 | -0.0015 | 0.0098 | 80% | not applicable |
| lock_in_placebo | strong_demand/wide_supply/none_reverse/low_noise | 20 | -0.0015 | 0.0098 | 80% | not applicable |
| lock_in_placebo | strong_demand/wide_supply/strong_reverse/high_noise | 20 | -0.0014 | 0.0096 | 80% | not applicable |
| lock_in_placebo | strong_demand/wide_supply/strong_reverse/low_noise | 20 | -0.0013 | 0.0097 | 80% | not applicable |
| lock_in_placebo | weak_demand/narrow_supply/mild_reverse/high_noise | 20 | +0.0014 | 0.0076 | 90% | not applicable |
| lock_in_placebo | weak_demand/narrow_supply/mild_reverse/low_noise | 20 | +0.0013 | 0.0076 | 90% | not applicable |
| lock_in_placebo | weak_demand/narrow_supply/none_reverse/high_noise | 20 | +0.0014 | 0.0075 | 90% | not applicable |
| lock_in_placebo | weak_demand/narrow_supply/none_reverse/low_noise | 20 | +0.0014 | 0.0075 | 90% | not applicable |
| lock_in_placebo | weak_demand/narrow_supply/strong_reverse/high_noise | 20 | +0.0012 | 0.0077 | 90% | not applicable |
| lock_in_placebo | weak_demand/narrow_supply/strong_reverse/low_noise | 20 | +0.0012 | 0.0076 | 90% | not applicable |
| lock_in_placebo | weak_demand/wide_supply/mild_reverse/high_noise | 20 | +0.0014 | 0.0076 | 90% | not applicable |
| lock_in_placebo | weak_demand/wide_supply/mild_reverse/low_noise | 20 | +0.0013 | 0.0076 | 90% | not applicable |
| lock_in_placebo | weak_demand/wide_supply/none_reverse/high_noise | 20 | +0.0014 | 0.0075 | 90% | not applicable |
| lock_in_placebo | weak_demand/wide_supply/none_reverse/low_noise | 20 | +0.0014 | 0.0075 | 90% | not applicable |
| lock_in_placebo | weak_demand/wide_supply/strong_reverse/high_noise | 20 | +0.0012 | 0.0076 | 90% | not applicable |
| lock_in_placebo | weak_demand/wide_supply/strong_reverse/low_noise | 20 | +0.0012 | 0.0076 | 90% | not applicable |
| migration_effect | strong_demand/narrow_supply/mild_reverse/high_noise | 20 | -0.0002 | 0.0034 | 100% | 5% |
| migration_effect | strong_demand/narrow_supply/mild_reverse/low_noise | 20 | 0.0000 | 0.0021 | 100% | 5% |
| migration_effect | strong_demand/narrow_supply/none_reverse/high_noise | 20 | -0.0003 | 0.0036 | 100% | 5% |
| migration_effect | strong_demand/narrow_supply/none_reverse/low_noise | 20 | +0.0001 | 0.0020 | 95% | 5% |
| migration_effect | strong_demand/narrow_supply/strong_reverse/high_noise | 20 | -0.0005 | 0.0026 | 100% | 85% |
| migration_effect | strong_demand/narrow_supply/strong_reverse/low_noise | 20 | -0.0010 | 0.0024 | 95% | 45% |
| migration_effect | strong_demand/wide_supply/mild_reverse/high_noise | 20 | -0.0003 | 0.0034 | 100% | 5% |
| migration_effect | strong_demand/wide_supply/mild_reverse/low_noise | 20 | 0.0000 | 0.0022 | 95% | 5% |
| migration_effect | strong_demand/wide_supply/none_reverse/high_noise | 20 | -0.0002 | 0.0035 | 100% | 5% |
| migration_effect | strong_demand/wide_supply/none_reverse/low_noise | 20 | +0.0002 | 0.0020 | 95% | 5% |
| migration_effect | strong_demand/wide_supply/strong_reverse/high_noise | 20 | -0.0010 | 0.0030 | 100% | 85% |
| migration_effect | strong_demand/wide_supply/strong_reverse/low_noise | 20 | -0.0015 | 0.0029 | 95% | 55% |
| migration_effect | weak_demand/narrow_supply/mild_reverse/high_noise | 20 | +0.0001 | 0.0032 | 95% | 5% |
| migration_effect | weak_demand/narrow_supply/mild_reverse/low_noise | 20 | +0.0001 | 0.0020 | 100% | 0% |
| migration_effect | weak_demand/narrow_supply/none_reverse/high_noise | 20 | 0.0000 | 0.0030 | 95% | 5% |
| migration_effect | weak_demand/narrow_supply/none_reverse/low_noise | 20 | +0.0002 | 0.0020 | 100% | 10% |
| migration_effect | weak_demand/narrow_supply/strong_reverse/high_noise | 20 | -0.0001 | 0.0034 | 95% | 40% |
| migration_effect | weak_demand/narrow_supply/strong_reverse/low_noise | 20 | -0.0004 | 0.0021 | 100% | 10% |
| migration_effect | weak_demand/wide_supply/mild_reverse/high_noise | 20 | +0.0001 | 0.0032 | 95% | 5% |
| migration_effect | weak_demand/wide_supply/mild_reverse/low_noise | 20 | +0.0001 | 0.0019 | 100% | 0% |
| migration_effect | weak_demand/wide_supply/none_reverse/high_noise | 20 | +0.0001 | 0.0030 | 95% | 5% |
| migration_effect | weak_demand/wide_supply/none_reverse/low_noise | 20 | +0.0002 | 0.0020 | 95% | 5% |
| migration_effect | weak_demand/wide_supply/strong_reverse/high_noise | 20 | -0.0004 | 0.0033 | 95% | 40% |
| migration_effect | weak_demand/wide_supply/strong_reverse/low_noise | 20 | -0.0007 | 0.0021 | 100% | 5% |
| migration_naive | strong_demand/narrow_supply/mild_reverse/high_noise | 20 | -0.0033 | 0.0046 | 85% | not applicable |
| migration_naive | strong_demand/narrow_supply/mild_reverse/low_noise | 20 | -0.0032 | 0.0039 | 55% | not applicable |
| migration_naive | strong_demand/narrow_supply/none_reverse/high_noise | 20 | -0.0040 | 0.0052 | 80% | not applicable |
| migration_naive | strong_demand/narrow_supply/none_reverse/low_noise | 20 | -0.0037 | 0.0043 | 65% | not applicable |
| migration_naive | strong_demand/narrow_supply/strong_reverse/high_noise | 20 | -0.0055 | 0.0059 | 20% | not applicable |
| migration_naive | strong_demand/narrow_supply/strong_reverse/low_noise | 20 | -0.0059 | 0.0062 | 5% | not applicable |
| migration_naive | strong_demand/wide_supply/mild_reverse/high_noise | 20 | -0.0033 | 0.0048 | 80% | not applicable |
| migration_naive | strong_demand/wide_supply/mild_reverse/low_noise | 20 | -0.0032 | 0.0040 | 55% | not applicable |
| migration_naive | strong_demand/wide_supply/none_reverse/high_noise | 20 | -0.0040 | 0.0052 | 80% | not applicable |
| migration_naive | strong_demand/wide_supply/none_reverse/low_noise | 20 | -0.0037 | 0.0043 | 70% | not applicable |
| migration_naive | strong_demand/wide_supply/strong_reverse/high_noise | 20 | -0.0058 | 0.0063 | 20% | not applicable |
| migration_naive | strong_demand/wide_supply/strong_reverse/low_noise | 20 | -0.0063 | 0.0067 | 5% | not applicable |
| migration_naive | weak_demand/narrow_supply/mild_reverse/high_noise | 20 | -0.0017 | 0.0028 | 100% | not applicable |
| migration_naive | weak_demand/narrow_supply/mild_reverse/low_noise | 20 | -0.0020 | 0.0023 | 95% | not applicable |
| migration_naive | weak_demand/narrow_supply/none_reverse/high_noise | 20 | -0.0019 | 0.0031 | 100% | not applicable |
| migration_naive | weak_demand/narrow_supply/none_reverse/low_noise | 20 | -0.0023 | 0.0029 | 90% | not applicable |
| migration_naive | weak_demand/narrow_supply/strong_reverse/high_noise | 20 | -0.0041 | 0.0044 | 40% | not applicable |
| migration_naive | weak_demand/narrow_supply/strong_reverse/low_noise | 20 | -0.0043 | 0.0043 | 5% | not applicable |
| migration_naive | weak_demand/wide_supply/mild_reverse/high_noise | 20 | -0.0019 | 0.0030 | 90% | not applicable |
| migration_naive | weak_demand/wide_supply/mild_reverse/low_noise | 20 | -0.0022 | 0.0025 | 90% | not applicable |
| migration_naive | weak_demand/wide_supply/none_reverse/high_noise | 20 | -0.0019 | 0.0031 | 100% | not applicable |
| migration_naive | weak_demand/wide_supply/none_reverse/low_noise | 20 | -0.0023 | 0.0029 | 90% | not applicable |
| migration_naive | weak_demand/wide_supply/strong_reverse/high_noise | 20 | -0.0044 | 0.0047 | 35% | not applicable |
| migration_naive | weak_demand/wide_supply/strong_reverse/low_noise | 20 | -0.0046 | 0.0048 | 5% | not applicable |
| migration_placebo | strong_demand/narrow_supply/mild_reverse/high_noise | 20 | -0.0028 | 0.0041 | 95% | not applicable |
| migration_placebo | strong_demand/narrow_supply/mild_reverse/low_noise | 20 | -0.0009 | 0.0022 | 95% | not applicable |
| migration_placebo | strong_demand/narrow_supply/none_reverse/high_noise | 20 | -0.0001 | 0.0035 | 95% | not applicable |
| migration_placebo | strong_demand/narrow_supply/none_reverse/low_noise | 20 | -0.0001 | 0.0022 | 95% | not applicable |
| migration_placebo | strong_demand/narrow_supply/strong_reverse/high_noise | 20 | -0.0102 | 0.0107 | 15% | not applicable |
| migration_placebo | strong_demand/narrow_supply/strong_reverse/low_noise | 20 | -0.0047 | 0.0054 | 55% | not applicable |
| migration_placebo | strong_demand/wide_supply/mild_reverse/high_noise | 20 | -0.0029 | 0.0042 | 95% | not applicable |
| migration_placebo | strong_demand/wide_supply/mild_reverse/low_noise | 20 | -0.0010 | 0.0023 | 95% | not applicable |
| migration_placebo | strong_demand/wide_supply/none_reverse/high_noise | 20 | -0.0002 | 0.0035 | 95% | not applicable |
| migration_placebo | strong_demand/wide_supply/none_reverse/low_noise | 20 | -0.0002 | 0.0022 | 95% | not applicable |
| migration_placebo | strong_demand/wide_supply/strong_reverse/high_noise | 20 | -0.0108 | 0.0113 | 15% | not applicable |
| migration_placebo | strong_demand/wide_supply/strong_reverse/low_noise | 20 | -0.0054 | 0.0060 | 45% | not applicable |
| migration_placebo | weak_demand/narrow_supply/mild_reverse/high_noise | 20 | -0.0025 | 0.0041 | 95% | not applicable |
| migration_placebo | weak_demand/narrow_supply/mild_reverse/low_noise | 20 | -0.0007 | 0.0022 | 100% | not applicable |
| migration_placebo | weak_demand/narrow_supply/none_reverse/high_noise | 20 | 0.0000 | 0.0031 | 95% | not applicable |
| migration_placebo | weak_demand/narrow_supply/none_reverse/low_noise | 20 | +0.0001 | 0.0023 | 90% | not applicable |
| migration_placebo | weak_demand/narrow_supply/strong_reverse/high_noise | 20 | -0.0066 | 0.0073 | 60% | not applicable |
| migration_placebo | weak_demand/narrow_supply/strong_reverse/low_noise | 20 | -0.0023 | 0.0030 | 90% | not applicable |
| migration_placebo | weak_demand/wide_supply/mild_reverse/high_noise | 20 | -0.0026 | 0.0041 | 95% | not applicable |
| migration_placebo | weak_demand/wide_supply/mild_reverse/low_noise | 20 | -0.0008 | 0.0022 | 100% | not applicable |
| migration_placebo | weak_demand/wide_supply/none_reverse/high_noise | 20 | -0.0001 | 0.0031 | 95% | not applicable |
| migration_placebo | weak_demand/wide_supply/none_reverse/low_noise | 20 | 0.0000 | 0.0023 | 95% | not applicable |
| migration_placebo | weak_demand/wide_supply/strong_reverse/high_noise | 20 | -0.0070 | 0.0076 | 60% | not applicable |
| migration_placebo | weak_demand/wide_supply/strong_reverse/low_noise | 20 | -0.0027 | 0.0034 | 95% | not applicable |
| ranking_adjusted | strong_demand/narrow_supply/mild_reverse/high_noise | 20 | -0.0374 | 0.0395 | not applicable | 90% |
| ranking_adjusted | strong_demand/narrow_supply/mild_reverse/low_noise | 20 | -0.0459 | 0.0494 | not applicable | 89% |
| ranking_adjusted | strong_demand/narrow_supply/none_reverse/high_noise | 20 | -0.0266 | 0.0279 | not applicable | 91% |
| ranking_adjusted | strong_demand/narrow_supply/none_reverse/low_noise | 20 | -0.0329 | 0.0357 | not applicable | 91% |
| ranking_adjusted | strong_demand/narrow_supply/strong_reverse/high_noise | 20 | -0.0939 | 0.1029 | not applicable | 81% |
| ranking_adjusted | strong_demand/narrow_supply/strong_reverse/low_noise | 20 | -0.1238 | 0.1430 | not applicable | 81% |
| ranking_adjusted | strong_demand/wide_supply/mild_reverse/high_noise | 20 | -0.0361 | 0.0386 | not applicable | 89% |
| ranking_adjusted | strong_demand/wide_supply/mild_reverse/low_noise | 20 | -0.0437 | 0.0472 | not applicable | 89% |
| ranking_adjusted | strong_demand/wide_supply/none_reverse/high_noise | 20 | -0.0267 | 0.0283 | not applicable | 91% |
| ranking_adjusted | strong_demand/wide_supply/none_reverse/low_noise | 20 | -0.0314 | 0.0337 | not applicable | 91% |
| ranking_adjusted | strong_demand/wide_supply/strong_reverse/high_noise | 20 | -0.0946 | 0.1047 | not applicable | 80% |
| ranking_adjusted | strong_demand/wide_supply/strong_reverse/low_noise | 20 | -0.1204 | 0.1360 | not applicable | 80% |
| ranking_adjusted | weak_demand/narrow_supply/mild_reverse/high_noise | 20 | -0.0280 | 0.0298 | not applicable | 91% |
| ranking_adjusted | weak_demand/narrow_supply/mild_reverse/low_noise | 20 | -0.0301 | 0.0314 | not applicable | 91% |
| ranking_adjusted | weak_demand/narrow_supply/none_reverse/high_noise | 20 | -0.0318 | 0.0337 | not applicable | 89% |
| ranking_adjusted | weak_demand/narrow_supply/none_reverse/low_noise | 20 | -0.0356 | 0.0374 | not applicable | 89% |
| ranking_adjusted | weak_demand/narrow_supply/strong_reverse/high_noise | 20 | -0.0214 | 0.0225 | not applicable | 92% |
| ranking_adjusted | weak_demand/narrow_supply/strong_reverse/low_noise | 20 | -0.0225 | 0.0236 | not applicable | 92% |
| ranking_adjusted | weak_demand/wide_supply/mild_reverse/high_noise | 20 | -0.0268 | 0.0283 | not applicable | 91% |
| ranking_adjusted | weak_demand/wide_supply/mild_reverse/low_noise | 20 | -0.0294 | 0.0308 | not applicable | 91% |
| ranking_adjusted | weak_demand/wide_supply/none_reverse/high_noise | 20 | -0.0314 | 0.0333 | not applicable | 89% |
| ranking_adjusted | weak_demand/wide_supply/none_reverse/low_noise | 20 | -0.0348 | 0.0361 | not applicable | 89% |
| ranking_adjusted | weak_demand/wide_supply/strong_reverse/high_noise | 20 | -0.0204 | 0.0217 | not applicable | 92% |
| ranking_adjusted | weak_demand/wide_supply/strong_reverse/low_noise | 20 | -0.0226 | 0.0239 | not applicable | 93% |
| self_report_correction | strong_demand/narrow_supply/mild_reverse/high_noise | 20 | -0.0010 | 0.0031 | not applicable | 2% |
| self_report_correction | strong_demand/narrow_supply/mild_reverse/low_noise | 20 | -0.0010 | 0.0031 | not applicable | 2% |
| self_report_correction | strong_demand/narrow_supply/none_reverse/high_noise | 20 | -0.0010 | 0.0031 | not applicable | 2% |
| self_report_correction | strong_demand/narrow_supply/none_reverse/low_noise | 20 | -0.0010 | 0.0031 | not applicable | 2% |
| self_report_correction | strong_demand/narrow_supply/strong_reverse/high_noise | 20 | -0.0010 | 0.0031 | not applicable | 2% |
| self_report_correction | strong_demand/narrow_supply/strong_reverse/low_noise | 20 | -0.0010 | 0.0031 | not applicable | 2% |
| self_report_correction | strong_demand/wide_supply/mild_reverse/high_noise | 20 | -0.0010 | 0.0031 | not applicable | 2% |
| self_report_correction | strong_demand/wide_supply/mild_reverse/low_noise | 20 | -0.0010 | 0.0031 | not applicable | 2% |
| self_report_correction | strong_demand/wide_supply/none_reverse/high_noise | 20 | -0.0010 | 0.0031 | not applicable | 2% |
| self_report_correction | strong_demand/wide_supply/none_reverse/low_noise | 20 | -0.0010 | 0.0031 | not applicable | 2% |
| self_report_correction | strong_demand/wide_supply/strong_reverse/high_noise | 20 | -0.0010 | 0.0031 | not applicable | 2% |
| self_report_correction | strong_demand/wide_supply/strong_reverse/low_noise | 20 | -0.0010 | 0.0031 | not applicable | 2% |
| self_report_correction | weak_demand/narrow_supply/mild_reverse/high_noise | 20 | -0.0021 | 0.0036 | not applicable | 2% |
| self_report_correction | weak_demand/narrow_supply/mild_reverse/low_noise | 20 | -0.0021 | 0.0036 | not applicable | 2% |
| self_report_correction | weak_demand/narrow_supply/none_reverse/high_noise | 20 | -0.0021 | 0.0036 | not applicable | 2% |
| self_report_correction | weak_demand/narrow_supply/none_reverse/low_noise | 20 | -0.0021 | 0.0036 | not applicable | 2% |
| self_report_correction | weak_demand/narrow_supply/strong_reverse/high_noise | 20 | -0.0021 | 0.0036 | not applicable | 2% |
| self_report_correction | weak_demand/narrow_supply/strong_reverse/low_noise | 20 | -0.0021 | 0.0036 | not applicable | 2% |
| self_report_correction | weak_demand/wide_supply/mild_reverse/high_noise | 20 | -0.0021 | 0.0036 | not applicable | 2% |
| self_report_correction | weak_demand/wide_supply/mild_reverse/low_noise | 20 | -0.0021 | 0.0036 | not applicable | 2% |
| self_report_correction | weak_demand/wide_supply/none_reverse/high_noise | 20 | -0.0021 | 0.0036 | not applicable | 2% |
| self_report_correction | weak_demand/wide_supply/none_reverse/low_noise | 20 | -0.0021 | 0.0036 | not applicable | 2% |
| self_report_correction | weak_demand/wide_supply/strong_reverse/high_noise | 20 | -0.0021 | 0.0036 | not applicable | 2% |
| self_report_correction | weak_demand/wide_supply/strong_reverse/low_noise | 20 | -0.0021 | 0.0036 | not applicable | 2% |
| severe_share | strong_demand/narrow_supply/mild_reverse/high_noise | 20 | 0.0000 | 0.0000 | 100% | not applicable |
| severe_share | strong_demand/narrow_supply/mild_reverse/low_noise | 20 | 0.0000 | 0.0000 | 100% | not applicable |
| severe_share | strong_demand/narrow_supply/none_reverse/high_noise | 20 | 0.0000 | 0.0000 | 100% | not applicable |
| severe_share | strong_demand/narrow_supply/none_reverse/low_noise | 20 | 0.0000 | 0.0000 | 100% | not applicable |
| severe_share | strong_demand/narrow_supply/strong_reverse/high_noise | 20 | 0.0000 | 0.0000 | 100% | not applicable |
| severe_share | strong_demand/narrow_supply/strong_reverse/low_noise | 20 | 0.0000 | 0.0000 | 100% | not applicable |
| severe_share | strong_demand/wide_supply/mild_reverse/high_noise | 20 | 0.0000 | 0.0000 | 100% | not applicable |
| severe_share | strong_demand/wide_supply/mild_reverse/low_noise | 20 | 0.0000 | 0.0000 | 100% | not applicable |
| severe_share | strong_demand/wide_supply/none_reverse/high_noise | 20 | 0.0000 | 0.0000 | 100% | not applicable |
| severe_share | strong_demand/wide_supply/none_reverse/low_noise | 20 | 0.0000 | 0.0000 | 100% | not applicable |
| severe_share | strong_demand/wide_supply/strong_reverse/high_noise | 20 | 0.0000 | 0.0000 | 100% | not applicable |
| severe_share | strong_demand/wide_supply/strong_reverse/low_noise | 20 | 0.0000 | 0.0000 | 100% | not applicable |
| severe_share | weak_demand/narrow_supply/mild_reverse/high_noise | 20 | 0.0000 | 0.0000 | 100% | not applicable |
| severe_share | weak_demand/narrow_supply/mild_reverse/low_noise | 20 | 0.0000 | 0.0000 | 100% | not applicable |
| severe_share | weak_demand/narrow_supply/none_reverse/high_noise | 20 | 0.0000 | 0.0000 | 100% | not applicable |
| severe_share | weak_demand/narrow_supply/none_reverse/low_noise | 20 | 0.0000 | 0.0000 | 100% | not applicable |
| severe_share | weak_demand/narrow_supply/strong_reverse/high_noise | 20 | 0.0000 | 0.0000 | 100% | not applicable |
| severe_share | weak_demand/narrow_supply/strong_reverse/low_noise | 20 | 0.0000 | 0.0000 | 100% | not applicable |
| severe_share | weak_demand/wide_supply/mild_reverse/high_noise | 20 | 0.0000 | 0.0000 | 100% | not applicable |
| severe_share | weak_demand/wide_supply/mild_reverse/low_noise | 20 | 0.0000 | 0.0000 | 100% | not applicable |
| severe_share | weak_demand/wide_supply/none_reverse/high_noise | 20 | 0.0000 | 0.0000 | 100% | not applicable |
| severe_share | weak_demand/wide_supply/none_reverse/low_noise | 20 | 0.0000 | 0.0000 | 100% | not applicable |
| severe_share | weak_demand/wide_supply/strong_reverse/high_noise | 20 | 0.0000 | 0.0000 | 100% | not applicable |
| severe_share | weak_demand/wide_supply/strong_reverse/low_noise | 20 | 0.0000 | 0.0000 | 100% | not applicable |
| supply_controlled | strong_demand/narrow_supply/mild_reverse/high_noise | 20 | +0.0051 | 0.0073 | 75% | not applicable |
| supply_controlled | strong_demand/narrow_supply/mild_reverse/low_noise | 20 | +0.0012 | 0.0023 | 85% | not applicable |
| supply_controlled | strong_demand/narrow_supply/none_reverse/high_noise | 20 | +0.0041 | 0.0068 | 80% | not applicable |
| supply_controlled | strong_demand/narrow_supply/none_reverse/low_noise | 20 | +0.0009 | 0.0021 | 90% | not applicable |
| supply_controlled | strong_demand/narrow_supply/strong_reverse/high_noise | 20 | +0.0062 | 0.0079 | 75% | not applicable |
| supply_controlled | strong_demand/narrow_supply/strong_reverse/low_noise | 20 | +0.0010 | 0.0025 | 90% | not applicable |
| supply_controlled | strong_demand/wide_supply/mild_reverse/high_noise | 20 | +0.0051 | 0.0070 | 75% | not applicable |
| supply_controlled | strong_demand/wide_supply/mild_reverse/low_noise | 20 | +0.0012 | 0.0022 | 85% | not applicable |
| supply_controlled | strong_demand/wide_supply/none_reverse/high_noise | 20 | +0.0042 | 0.0066 | 80% | not applicable |
| supply_controlled | strong_demand/wide_supply/none_reverse/low_noise | 20 | +0.0010 | 0.0021 | 90% | not applicable |
| supply_controlled | strong_demand/wide_supply/strong_reverse/high_noise | 20 | +0.0061 | 0.0075 | 70% | not applicable |
| supply_controlled | strong_demand/wide_supply/strong_reverse/low_noise | 20 | +0.0011 | 0.0023 | 90% | not applicable |
| supply_controlled | weak_demand/narrow_supply/mild_reverse/high_noise | 20 | +0.0036 | 0.0058 | 85% | not applicable |
| supply_controlled | weak_demand/narrow_supply/mild_reverse/low_noise | 20 | +0.0007 | 0.0016 | 95% | not applicable |
| supply_controlled | weak_demand/narrow_supply/none_reverse/high_noise | 20 | +0.0019 | 0.0047 | 90% | not applicable |
| supply_controlled | weak_demand/narrow_supply/none_reverse/low_noise | 20 | +0.0003 | 0.0015 | 90% | not applicable |
| supply_controlled | weak_demand/narrow_supply/strong_reverse/high_noise | 20 | +0.0056 | 0.0075 | 75% | not applicable |
| supply_controlled | weak_demand/narrow_supply/strong_reverse/low_noise | 20 | +0.0010 | 0.0017 | 95% | not applicable |
| supply_controlled | weak_demand/wide_supply/mild_reverse/high_noise | 20 | +0.0037 | 0.0060 | 85% | not applicable |
| supply_controlled | weak_demand/wide_supply/mild_reverse/low_noise | 20 | +0.0008 | 0.0016 | 90% | not applicable |
| supply_controlled | weak_demand/wide_supply/none_reverse/high_noise | 20 | +0.0021 | 0.0050 | 90% | not applicable |
| supply_controlled | weak_demand/wide_supply/none_reverse/low_noise | 20 | +0.0005 | 0.0016 | 90% | not applicable |
| supply_controlled | weak_demand/wide_supply/strong_reverse/high_noise | 20 | +0.0051 | 0.0072 | 70% | not applicable |
| supply_controlled | weak_demand/wide_supply/strong_reverse/low_noise | 20 | +0.0010 | 0.0017 | 95% | not applicable |
| supply_uncontrolled | strong_demand/narrow_supply/mild_reverse/high_noise | 20 | +0.0095 | 0.0114 | 65% | not applicable |
| supply_uncontrolled | strong_demand/narrow_supply/mild_reverse/low_noise | 20 | +0.0046 | 0.0057 | 70% | not applicable |
| supply_uncontrolled | strong_demand/narrow_supply/none_reverse/high_noise | 20 | +0.0073 | 0.0094 | 70% | not applicable |
| supply_uncontrolled | strong_demand/narrow_supply/none_reverse/low_noise | 20 | +0.0042 | 0.0051 | 65% | not applicable |
| supply_uncontrolled | strong_demand/narrow_supply/strong_reverse/high_noise | 20 | +0.0146 | 0.0160 | 30% | not applicable |
| supply_uncontrolled | strong_demand/narrow_supply/strong_reverse/low_noise | 20 | +0.0069 | 0.0081 | 55% | not applicable |
| supply_uncontrolled | strong_demand/wide_supply/mild_reverse/high_noise | 20 | +0.0094 | 0.0110 | 65% | not applicable |
| supply_uncontrolled | strong_demand/wide_supply/mild_reverse/low_noise | 20 | +0.0045 | 0.0055 | 70% | not applicable |
| supply_uncontrolled | strong_demand/wide_supply/none_reverse/high_noise | 20 | +0.0072 | 0.0091 | 70% | not applicable |
| supply_uncontrolled | strong_demand/wide_supply/none_reverse/low_noise | 20 | +0.0042 | 0.0050 | 60% | not applicable |
| supply_uncontrolled | strong_demand/wide_supply/strong_reverse/high_noise | 20 | +0.0142 | 0.0153 | 40% | not applicable |
| supply_uncontrolled | strong_demand/wide_supply/strong_reverse/low_noise | 20 | +0.0072 | 0.0080 | 45% | not applicable |
| supply_uncontrolled | weak_demand/narrow_supply/mild_reverse/high_noise | 20 | +0.0056 | 0.0070 | 80% | not applicable |
| supply_uncontrolled | weak_demand/narrow_supply/mild_reverse/low_noise | 20 | +0.0018 | 0.0022 | 90% | not applicable |
| supply_uncontrolled | weak_demand/narrow_supply/none_reverse/high_noise | 20 | +0.0030 | 0.0048 | 90% | not applicable |
| supply_uncontrolled | weak_demand/narrow_supply/none_reverse/low_noise | 20 | +0.0014 | 0.0019 | 90% | not applicable |
| supply_uncontrolled | weak_demand/narrow_supply/strong_reverse/high_noise | 20 | +0.0090 | 0.0104 | 60% | not applicable |
| supply_uncontrolled | weak_demand/narrow_supply/strong_reverse/low_noise | 20 | +0.0024 | 0.0028 | 85% | not applicable |
| supply_uncontrolled | weak_demand/wide_supply/mild_reverse/high_noise | 20 | +0.0056 | 0.0072 | 80% | not applicable |
| supply_uncontrolled | weak_demand/wide_supply/mild_reverse/low_noise | 20 | +0.0019 | 0.0022 | 90% | not applicable |
| supply_uncontrolled | weak_demand/wide_supply/none_reverse/high_noise | 20 | +0.0032 | 0.0051 | 90% | not applicable |
| supply_uncontrolled | weak_demand/wide_supply/none_reverse/low_noise | 20 | +0.0015 | 0.0019 | 90% | not applicable |
| supply_uncontrolled | weak_demand/wide_supply/strong_reverse/high_noise | 20 | +0.0086 | 0.0099 | 60% | not applicable |
| supply_uncontrolled | weak_demand/wide_supply/strong_reverse/low_noise | 20 | +0.0026 | 0.0028 | 75% | not applicable |
| under_35_shift | strong_demand/narrow_supply/mild_reverse/high_noise | 20 | -0.0005 | 0.0021 | 80% | not applicable |
| under_35_shift | strong_demand/narrow_supply/mild_reverse/low_noise | 20 | -0.0007 | 0.0018 | 80% | not applicable |
| under_35_shift | strong_demand/narrow_supply/none_reverse/high_noise | 20 | -0.0010 | 0.0020 | 85% | not applicable |
| under_35_shift | strong_demand/narrow_supply/none_reverse/low_noise | 20 | -0.0010 | 0.0020 | 85% | not applicable |
| under_35_shift | strong_demand/narrow_supply/strong_reverse/high_noise | 20 | +0.0004 | 0.0016 | 90% | not applicable |
| under_35_shift | strong_demand/narrow_supply/strong_reverse/low_noise | 20 | +0.0005 | 0.0022 | 80% | not applicable |
| under_35_shift | strong_demand/wide_supply/mild_reverse/high_noise | 20 | -0.0012 | 0.0024 | 60% | not applicable |
| under_35_shift | strong_demand/wide_supply/mild_reverse/low_noise | 20 | -0.0006 | 0.0021 | 80% | not applicable |
| under_35_shift | strong_demand/wide_supply/none_reverse/high_noise | 20 | -0.0010 | 0.0020 | 85% | not applicable |
| under_35_shift | strong_demand/wide_supply/none_reverse/low_noise | 20 | -0.0010 | 0.0020 | 85% | not applicable |
| under_35_shift | strong_demand/wide_supply/strong_reverse/high_noise | 20 | +0.0002 | 0.0014 | 95% | not applicable |
| under_35_shift | strong_demand/wide_supply/strong_reverse/low_noise | 20 | +0.0003 | 0.0017 | 100% | not applicable |
| under_35_shift | weak_demand/narrow_supply/mild_reverse/high_noise | 20 | +0.0002 | 0.0013 | 90% | not applicable |
| under_35_shift | weak_demand/narrow_supply/mild_reverse/low_noise | 20 | +0.0006 | 0.0020 | 70% | not applicable |
| under_35_shift | weak_demand/narrow_supply/none_reverse/high_noise | 20 | +0.0003 | 0.0016 | 85% | not applicable |
| under_35_shift | weak_demand/narrow_supply/none_reverse/low_noise | 20 | +0.0003 | 0.0016 | 85% | not applicable |
| under_35_shift | weak_demand/narrow_supply/strong_reverse/high_noise | 20 | +0.0004 | 0.0013 | 100% | not applicable |
| under_35_shift | weak_demand/narrow_supply/strong_reverse/low_noise | 20 | -0.0002 | 0.0016 | 90% | not applicable |
| under_35_shift | weak_demand/wide_supply/mild_reverse/high_noise | 20 | -0.0002 | 0.0015 | 90% | not applicable |
| under_35_shift | weak_demand/wide_supply/mild_reverse/low_noise | 20 | +0.0003 | 0.0016 | 80% | not applicable |
| under_35_shift | weak_demand/wide_supply/none_reverse/high_noise | 20 | +0.0003 | 0.0016 | 85% | not applicable |
| under_35_shift | weak_demand/wide_supply/none_reverse/low_noise | 20 | +0.0003 | 0.0016 | 85% | not applicable |
| under_35_shift | weak_demand/wide_supply/strong_reverse/high_noise | 20 | +0.0001 | 0.0018 | 90% | not applicable |
| under_35_shift | weak_demand/wide_supply/strong_reverse/low_noise | 20 | -0.0005 | 0.0018 | 95% | not applicable |

*Source: the simulated metros with known truth, the recovery study, every condition and seed, 20 seeds, as of 2026-10-22.*

## The data

| Source | Rule | Flagged | Rows |
|---|---|---:|---:|
| acs | jam_value | 7 | 2,415,786 |
| acs | moe_exceeds_estimate | 108,627 | 2,415,786 |
| acs | negative_moe | 0 | 2,415,786 |
| bps | county_listed_twice | 10 | 81,768 |
| bps | imputed_share_high | 8,045 | 81,768 |
| bps | malformed_fips | 0 | 81,768 |
| bps | negative_units | 0 | 81,768 |
| fhfa | implausible_jump | 15 | 85,272 |
| fhfa | missing_quarter | 61 | 85,272 |
| fhfa | non_positive_index | 0 | 85,272 |
| hmda | income_exempt_or_missing | 4,893,629 | 64,743,292 |
| hmda | metro_unresolved | 2,310,292 | 64,743,292 |
| hmda | not_principal_residence | 6,717,971 | 64,743,292 |
| hmda | rate_missing | 2,083,671 | 64,743,292 |
| hmda | reverse_open_or_business | 3,275,856 | 64,743,292 |
| hmda | term_not_30_years | 13,859,990 | 64,743,292 |
| hmda | value_below_loan | 984,896 | 64,743,292 |
| hud_fmr | bedroom_order | 0 | 4,764 |
| hud_fmr | non_positive_rent | 0 | 4,764 |
| hud_il | limit_order | 0 | 84,224 |
| hud_il | non_positive_income | 0 | 84,224 |
| omb | county_in_two_areas | 0 | 13,288 |
| omb | malformed_fips | 0 | 13,288 |
| pmms | implausible_rate | 0 | 2,900 |
| pmms | missing_week | 0 | 2,900 |
| popest | non_positive_population | 0 | 81,714 |
| popest | vintage_overlap | 0 | 81,714 |

*Source: several sources, every row of every source, as of 2026-10-23.* The report by source and year is `results/marts/mart_quarantine.parquet`, shown on the data page.

Sources and their latest periods: FHFA 2026Q2, PMMS 2026-10-22 (latest rate 7.32%), ACS 2024, HUD fair market rents FY2027, HUD income limits FY2026, permits 2026 through month 8, population 2025, HMDA 2025. 7 delineation vintages, the latest 2,023 with 393 metropolitan and 542 micropolitan areas. 575 files read, 2,573,273,827 bytes, each with its checksum in `data/PROVENANCE.md`. Mortgage rates: Freddie Mac Primary Mortgage Market Survey, used under its terms of use.

## The warehouse and the metric layer

35 models, 164 tests, 0 failed. 21 metrics, each defined over the finest grain and over the shipped mart, reconciled at 4 grains: 1,764 cells compared, 0 disagreements.

| Metric | Over the grain | Over the mart |
|---|---|---|
| households | sum(estimate) filter (where variable = 'B11001_001') | sum(households) |
| owner households | sum(estimate) filter (where variable = 'B25003_002') | sum(owner_households) |
| renter households | sum(estimate) filter (where variable = 'B25003_003') | sum(renter_households) |
| renters burdened | sum(estimate) filter (where variable in ('B25070_007', 'B25070_008', 'B25070_009', 'B25070_010')) | sum(renters_burdened) |
| renters severe | sum(estimate) filter (where variable = 'B25070_010') | sum(renters_severe) |
| renter burdened share | sum(estimate) filter (where variable in ('B25070_007', 'B25070_008', 'B25070_009', 'B25070_010')) / (sum(estimate) filter (where variable = 'B25070_001') - coalesce(sum(estimate) filter (where variable = 'B25070_011'), 0)) | sum(renters_burdened) / sum(renters_with_share) |
| housing units | sum(estimate) filter (where variable = 'B25001_001') | sum(housing_units) |
| permits | sum(permits) | sum(permits) |
| population | sum(population) | sum(population) |
| domestic migration | sum(domestic_migration) | sum(domestic_migration) |
| purchase loans | count(*) filter (where loan_purpose = 1) | sum(purchase_loans) |
| refinance loans | count(*) filter (where loan_purpose in (31, 32)) | sum(refinance_loans) |
| low rate originations | count(*) filter (where interest_rate < 4.0 and not q_rate_missing and not q_term_not_30_years) | sum(low_rate_originations) |
| turnover per 100 owners | 100.0 * sum(purchase_loans) / sum(owner_households) | 100.0 * sum(purchase_loans) / sum(owner_households) |
| lock in per 100 owners | 100.0 * sum(low_rate_originations) / sum(owner_households) | 100.0 * sum(low_rate_originations) / sum(owner_households) |
| permits per 100 households | 100.0 * sum(permits) / sum(households) | 100.0 * sum(permits) / sum(households) |
| domestic migration per 100 | 100.0 * sum(domestic_migration) / sum(population) | 100.0 * sum(domestic_migration) / sum(population) |
| purchase under 35 share | sum(purchase_under_35) / sum(purchase_with_age) | sum(purchase_under_35) / sum(purchase_with_age) |
| owner mortgage burdened share | sum(owners_mortgage_burdened) / sum(owners_mortgage_with_share) | sum(owners_mortgage_burdened) / sum(owners_mortgage_with_share) |
| payment share ratio of sums | 12.0 * sum(payment) / sum(median_income) | 12.0 * sum(payment) / sum(median_income) |
| price to income ratio of sums | sum(value_anchored) / sum(median_income) | sum(value_anchored) / sum(median_income) |

## Chapter tables

### Affordable is a decision

| Anchor year | Latest payment share | 2006 payment share | Difference | Metros above 2006 | Note |
|---:|---:|---:|---:|---:|---|
| 2,015 | 35.0% | 33.8% | +1.1 pts | 283 |  |
| 2,017 | 34.8% | 33.7% | +1.1 pts | 283 |  |
| 2,019 | 34.9% | 33.7% | +1.1 pts | 283 | chosen |
| 2,023 | 33.5% | 32.3% | +1.2 pts | 283 |  |

| Line | Metros above | Share |
|---:|---:|---:|
| 25% | 263 | 69% |
| 28% | 191 | 50% |
| 30% | 161 | 42% |
| 35% | 94 | 25% |

### The rate shock and the lock in

| Quarter | Rate | Payment | Price part | Rate part |
|---:|---:|---:|---:|---:|
| 2019Q1 | 4.37% | $1,316 | $0 | $0 |
| 2019Q2 | 4.01% | $1,279 | +$19 | -$57 |
| 2019Q3 | 3.66% | $1,239 | +$35 | -$112 |
| 2019Q4 | 3.70% | $1,255 | +$45 | -$106 |
| 2020Q1 | 3.52% | $1,241 | +$60 | -$135 |
| 2020Q2 | 3.24% | $1,209 | +$73 | -$180 |
| 2020Q3 | 2.95% | $1,184 | +$95 | -$227 |
| 2020Q4 | 2.76% | $1,180 | +$125 | -$261 |
| 2021Q1 | 2.88% | $1,226 | +$160 | -$249 |
| 2021Q2 | 3.00% | $1,315 | +$240 | -$241 |
| 2021Q3 | 2.87% | $1,362 | +$323 | -$277 |
| 2021Q4 | 3.08% | $1,445 | +$378 | -$249 |
| 2022Q1 | 3.82% | $1,643 | +$440 | -$113 |
| 2022Q2 | 5.27% | $2,074 | +$556 | +$202 |
| 2022Q3 | 5.62% | $2,176 | +$571 | +$288 |
| 2022Q4 | 6.66% | $2,396 | +$544 | +$536 |
| 2023Q1 | 6.37% | $2,332 | +$550 | +$465 |
| 2023Q2 | 6.51% | $2,437 | +$607 | +$514 |
| 2023Q3 | 7.04% | $2,611 | +$635 | +$660 |
| 2023Q4 | 7.30% | $2,683 | +$637 | +$730 |
| 2024Q1 | 6.75% | $2,575 | +$666 | +$593 |
| 2024Q2 | 7.00% | $2,702 | +$712 | +$674 |
| 2024Q3 | 6.51% | $2,595 | +$732 | +$547 |
| 2024Q4 | 6.63% | $2,640 | +$741 | +$583 |
| 2025Q1 | 6.83% | $2,712 | +$755 | +$641 |
| 2025Q2 | 6.79% | $2,739 | +$784 | +$639 |
| 2025Q3 | 6.57% | $2,688 | +$793 | +$580 |
| 2025Q4 | 6.23% | $2,610 | +$805 | +$489 |
| 2026Q1 | 6.11% | $2,597 | +$821 | +$460 |
| 2026Q2 | 6.41% | $2,704 | +$839 | +$549 |

| Threshold | Coefficient | Low | High | Placebo | Note |
|---:|---:|---:|---:|---:|---|
| 3.00% | -0.094 | -0.146 | -0.042 | +0.001 |  |
| 3.50% | -0.067 | -0.096 | -0.038 | +0.001 |  |
| 4.00% | -0.056 | -0.077 | -0.034 | +0.001 | chosen |

### The rent burden is a distribution problem

| Year | Under 30 percent | 30 to 50 percent | 50 percent and over |
|---:|---:|---:|---:|
| 2005 | 50.5% | 24.4% | 25.1% |
| 2006 | 50.2% | 24.6% | 25.1% |
| 2007 | 50.7% | 24.8% | 24.6% |
| 2008 | 50.2% | 24.7% | 25.1% |
| 2009 | 48.5% | 25.2% | 26.4% |
| 2010 | 47.0% | 25.5% | 27.4% |
| 2011 | 46.6% | 25.4% | 28.0% |
| 2012 | 48.0% | 25.0% | 27.0% |
| 2013 | 48.5% | 25.1% | 26.5% |
| 2014 | 48.2% | 25.4% | 26.3% |
| 2015 | 49.4% | 25.1% | 25.5% |
| 2016 | 50.3% | 24.8% | 25.0% |
| 2017 | 50.5% | 24.9% | 24.7% |
| 2018 | 50.3% | 24.9% | 24.8% |
| 2019 | 51.6% | 24.7% | 23.7% |
| 2021 | 48.9% | 24.9% | 26.1% |
| 2022 | 48.1% | 25.2% | 26.7% |
| 2023 | 48.2% | 25.3% | 26.4% |
| 2024 | 48.2% | 25.7% | 26.1% |

| Income group | Renters | Burdened | Severely burdened |
|---|---:|---:|---:|
| under 10k | 2,100,866 | 97.8% | 93.5% |
| 10k to 20k | 3,318,512 | 86.6% | 70.5% |
| 20k to 35k | 4,575,863 | 88.3% | 59.8% |
| 35k to 50k | 4,532,267 | 78.0% | 30.8% |
| 50k to 75k | 6,509,505 | 56.1% | 10.3% |
| 75k to 100k | 4,512,280 | 30.6% | 3.2% |
| 100k plus | 9,407,120 | 9.7% | 0.9% |

| Stated line | Severe share | Interval against the line | Note |
|---:|---:|---|---|
| 15% | 26.5% | clears |  |
| 20% | 26.5% | clears | chosen |
| 25% | 26.5% | clears |  |

### Where builders kept pace, prices rose less

| Specification | Annual growth per permit per 100 households | Low | High | Over the window | Clusters |
|---|---:|---:|---:|---:|---:|
| with the demand control | -0.0160 | -0.0286 | -0.0034 | -8.0% | 85 |
| without the demand control | -0.0009 | -0.0092 | +0.0074 | -0.4% | 85 |

| Window years | Controlled | Low | High | Uncontrolled | Note |
|---:|---:|---:|---:|---:|---|
| 3 | 0.0000 | -0.0131 | +0.0131 | +0.0113 | degenerate |
| 5 | -0.0160 | -0.0286 | -0.0034 | -0.0009 | chosen |
| 7 | +0.0016 | -0.0127 | +0.0159 | +0.0100 |  |

### The fair ranking

| Metro | Households | Median home | Median income | Payment share | Low | High | Raw rank | Adjusted rank | Interval | Moves |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| Los Angeles-Long Beach-Anaheim, CA | 4,583,939 | $984,121 | $96,405 | 71.3% | 70.4% | 72.2% | 7 | 2 | 1 to 4 | yes |
| San Diego-Chula Vista-Carlsbad, CA | 1,185,092 | $985,575 | $109,132 | 63.1% | 61.7% | 64.5% | 6 | 8 | 6 to 10 | no |
| San Francisco-Oakland-Fremont, CA | 1,770,425 | $1,161,939 | $135,590 | 59.9% | 58.6% | 61.2% | 2 | 10 | 10 to 12 | yes |
| New York-Newark-Jersey City, NY-NJ | 7,486,828 | $709,339 | $99,852 | 49.6% | 49.1% | 50.2% | 18 | 21 | 18 to 24 | no |
| Miami-Fort Lauderdale-West Palm Beach, FL | 2,382,154 | $570,254 | $80,625 | 49.4% | 48.6% | 50.2% | 33 | 22 | 18 to 25 | yes |
| Seattle-Tacoma-Bellevue, WA | 1,658,652 | $747,400 | $112,388 | 46.4% | 45.2% | 47.8% | 15 | 27 | 24 to 33 | yes |
| Riverside-San Bernardino-Ontario, CA | 1,484,661 | $601,161 | $91,013 | 46.1% | 45.4% | 46.9% | 29 | 28 | 25 to 33 | no |
| Boston-Cambridge-Newton, MA-NH | 1,970,240 | $724,836 | $117,825 | 43.0% | 41.9% | 44.1% | 16 | 41 | 35 to 47 | yes |
| Denver-Aurora-Centennial, CO | 1,265,606 | $625,144 | $108,046 | 40.4% | 39.4% | 41.4% | 23 | 52 | 47 to 61 | yes |
| Phoenix-Mesa-Chandler, AZ | 1,967,378 | $482,839 | $90,133 | 37.4% | 36.7% | 38.1% | 58 | 70 | 65 to 80 | yes |
| Tampa-St. Petersburg-Clearwater, FL | 1,377,328 | $400,907 | $78,275 | 35.8% | 34.7% | 36.9% | 106 | 90 | 76 to 100 | yes |
| Washington-Arlington-Alexandria, DC-VA-MD-WV | 2,415,530 | $619,214 | $126,244 | 34.3% | 33.7% | 34.8% | 25 | 102 | 96 to 113 | yes |
| Atlanta-Sandy Springs-Roswell, GA | 2,390,346 | $409,790 | $92,344 | 31.0% | 30.5% | 31.5% | 96 | 147 | 139 to 157 | yes |
| Philadelphia-Camden-Wilmington, PA-NJ-DE-MD | 2,505,818 | $402,523 | $90,850 | 30.9% | 30.4% | 31.5% | 104 | 149 | 139 to 159 | yes |
| Dallas-Fort Worth-Arlington, TX | 3,012,855 | $393,024 | $92,733 | 29.6% | 29.0% | 30.2% | 113 | 172 | 158 to 180 | yes |
| Chicago-Naperville-Elgin, IL-IN | 3,690,402 | $365,617 | $90,770 | 28.1% | 27.7% | 28.5% | 131 | 191 | 184 to 205 | yes |
| Minneapolis-St. Paul-Bloomington, MN-WI | 1,508,526 | $391,204 | $97,928 | 27.9% | 27.3% | 28.5% | 114 | 195 | 185 to 213 | yes |
| Houston-Pasadena-The Woodlands, TX | 2,768,708 | $313,177 | $81,417 | 26.9% | 26.4% | 27.3% | 174 | 216 | 209 to 232 | yes |
| Detroit-Warren-Dearborn, MI | 1,777,768 | $284,812 | $76,403 | 26.0% | 25.5% | 26.6% | 204 | 238 | 225 to 253 | yes |
| St. Louis, MO-IL | 1,178,246 | $271,172 | $81,679 | 23.2% | 22.6% | 23.8% | 223 | 307 | 289 to 318 | yes |

### Who still buys

| Year | Loans | Lenders | Income ratio | Low | High | Under 35 | Above twice the median | Value to income | Spread p50 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2018 | 3,389,103 | 5,148 | 1.28x | 1.25x | 1.32x | 38.4% | 22.7% | 3.38x | 0.44% |
| 2019 | 3,533,474 | 5,029 | 1.23x | 1.20x | 1.27x | 38.3% | 20.9% | 3.38x | 0.44% |
| 2020 | 3,861,776 | 4,164 | 1.24x | 1.22x | 1.28x | 40.7% | 21.4% | 3.62x | 0.31% |
| 2021 | 4,097,757 | 4,075 | 1.24x | 1.22x | 1.26x | 39.0% | 21.2% | 3.88x | 0.31% |
| 2022 | 3,317,262 | 4,160 | 1.32x | 1.30x | 1.35x | 38.9% | 23.8% | 3.62x | 0.31% |
| 2023 | 2,664,039 | 4,605 | 1.38x | 1.35x | 1.40x | 39.8% | 25.5% | 3.38x | 0.19% |
| 2024 | 2,695,601 | 4,433 | 1.36x | 1.33x | 1.38x | 39.7% | 25.1% | 3.38x | 0.19% |
| 2025 | 2,722,577 | 4,341 | 1.39x | 1.37x | 1.41x | 39.4% | 26.7% | 3.38x | 0.19% |

| Metro | Ratio 2019 | Ratio 2025 | Low | High | Change | Under 35 2025 |
|---|---:|---:|---:|---:|---:|---:|
| New York-Newark-Jersey City, NY-NJ | 1.47x | 1.78x | 1.73x | 1.88x | +0.30 | 36.4% |
| Dallas-Fort Worth-Arlington, TX | 1.35x | 1.37x | 1.27x | 1.48x | +0.03 | 38.3% |
| Chicago-Naperville-Elgin, IL-IN | 1.16x | 1.29x | 1.24x | 1.35x | +0.13 | 40.5% |
| Houston-Pasadena-The Woodlands, TX | 1.34x | 1.44x | 1.38x | 1.57x | +0.11 | 37.9% |
| Atlanta-Sandy Springs-Roswell, GA | 1.15x | 1.27x | 1.22x | 1.33x | +0.12 | 35.2% |
| Phoenix-Mesa-Chandler, AZ | 1.14x | 1.30x | 1.25x | 1.36x | +0.16 | 37.5% |
| Washington-Arlington-Alexandria, DC-VA-MD-WV | 1.06x | 1.25x | 1.21x | 1.29x | +0.18 | 34.5% |
| Philadelphia-Camden-Wilmington, PA-NJ-DE-MD | 1.17x | 1.35x | 1.29x | 1.40x | +0.17 | 41.1% |
| Los Angeles-Long Beach-Anaheim, CA | 1.77x | 2.20x | 2.10x | 2.36x | +0.44 | 30.2% |
| Minneapolis-St. Paul-Bloomington, MN-WI | 1.05x | 1.15x | 1.15x | 1.20x | +0.10 | 43.7% |
| Detroit-Warren-Dearborn, MI | 1.14x | 1.28x | 1.21x | 1.34x | +0.13 | 44.3% |
| Miami-Fort Lauderdale-West Palm Beach, FL | 1.45x | 1.83x | 1.71x | 1.89x | +0.37 | 29.2% |
| Tampa-St. Petersburg-Clearwater, FL | 1.34x | 1.44x | 1.37x | 1.50x | +0.10 | 33.8% |
| Seattle-Tacoma-Bellevue, WA | 1.25x | 1.53x | 1.45x | 1.62x | +0.29 | 38.7% |
| Boston-Cambridge-Newton, MA-NH | 1.30x | 1.46x | 1.38x | 1.51x | +0.17 | 38.5% |
| Denver-Aurora-Centennial, CO | 1.14x | 1.32x | 1.27x | 1.37x | +0.18 | 40.8% |
| Charlotte-Concord-Gastonia, NC-SC | 1.24x | 1.43x | 1.37x | 1.48x | +0.18 | 38.2% |
| Riverside-San Bernardino-Ontario, CA | 1.30x | 1.57x | 1.51x | 1.57x | +0.26 | 34.8% |
| San Antonio-New Braunfels, TX | 1.32x | 1.31x | 1.18x | 1.44x | -0.01 | 40.3% |
| St. Louis, MO-IL | 1.17x | 1.19x | 1.13x | 1.25x | +0.03 | 44.1% |

### The migration shock

| Window | Growth per person per 100 residents of shock | Low | High | p | Clusters |
|---|---:|---:|---:|---:|---:|
| 2019Q4 to 2021Q4 | +1.48% | +0.40% | +2.55% | 0.007 | 85 |
| 2016Q4 to 2018Q4 (placebo) | -0.78% | -1.35% | -0.20% | 0.009 | 85 |
| 2019Q4 to 2021Q4 (level alone, no pre pandemic control) | +2.41% | +1.87% | +2.95% | 0.000 | 85 |

| Metro | Mean post gap | Peak gap | Peak quarter | Latest gap | Reversal since peak | Permutation p | Donors searched | Top weights |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| Panama City-Panama City Beach, FL | +0.7% | +9.4% | 2023Q2 | -2.0% | +11.3 pts | 0.829 | 192 | Boise City 0.31; Michigan City-La Porte 0.25; Monroe 0.18 |
| Amherst Town-Northampton, MA | -1.2% | +1.5% | 2024Q2 | +0.9% | +0.6 pts | 0.725 | 192 | Lebanon 0.27; Dover 0.18; Roanoke 0.14 |
| Fairbanks-College, AK | -4.7% | +0.5% | 2020Q3 | -6.0% | +6.5 pts | 0.254 | 192 | Hattiesburg 0.31; Victoria 0.30; Florence 0.20 |

### The reader decision

| Metro | Median home | Affordable price | Can afford | Affordable share | Down payment years | Breakeven | Low | High |
|---|---:|---:|---|---:|---:|---:|---:|---:|
| Boston-Cambridge-Newton, MA-NH | $724,836 | $506,109 | no | 34% | 9.9 years | 21.0 years | 2.0 years | beyond 30 years |
| Chicago-Naperville-Elgin, IL-IN | $365,617 | $389,896 | yes | 53% | 6.5 years | 19.5 years | 2.0 years | beyond 30 years |
| San Francisco-Oakland-Fremont, CA | $1,161,939 | $582,418 | no | 16% | 12.4 years | 18.0 years | 1.0 years | beyond 30 years |
| Minneapolis-St. Paul-Bloomington, MN-WI | $391,204 | $420,643 | yes | 54% | 6.9 years | 18.0 years | 2.0 years | beyond 30 years |
| St. Louis, MO-IL | $271,172 | $350,847 | yes | 61% | 5.6 years | 17.0 years | 2.0 years | beyond 30 years |
| New York-Newark-Jersey City, NY-NJ | $709,339 | $428,907 | no | 30% | 10.6 years | 16.0 years | 2.0 years | beyond 30 years |
| Denver-Aurora-Centennial, CO | $625,144 | $464,104 | no | 36% | 8.6 years | 12.0 years | 2.0 years | beyond 30 years |
| Washington-Arlington-Alexandria, DC-VA-MD-WV | $619,214 | $542,273 | no | 44% | 7.6 years | 11.0 years | 1.0 years | beyond 30 years |
| Detroit-Warren-Dearborn, MI | $284,812 | $328,184 | yes | 56% | 6.3 years | 11.0 years | 2.0 years | beyond 30 years |
| Houston-Pasadena-The Woodlands, TX | $313,177 | $349,721 | yes | 55% | 6.0 years | 8.0 years | 2.0 years | 24.0 years |
| Philadelphia-Camden-Wilmington, PA-NJ-DE-MD | $402,523 | $390,240 | no | 49% | 7.3 years | 8.0 years | 1.0 years | beyond 30 years |
| San Diego-Chula Vista-Carlsbad, CA | $985,575 | $468,769 | no | 16% | 12.1 years | 7.0 years | 1.0 years | beyond 30 years |
| Los Angeles-Long Beach-Anaheim, CA | $984,121 | $414,101 | no | 14% | 13.6 years | 6.5 years | 1.0 years | beyond 30 years |
| Dallas-Fort Worth-Arlington, TX | $393,024 | $398,328 | yes | 51% | 6.2 years | 6.0 years | 1.0 years | beyond 30 years |
| Atlanta-Sandy Springs-Roswell, GA | $409,790 | $396,657 | no | 49% | 6.6 years | 6.0 years | 1.0 years | beyond 30 years |
| Seattle-Tacoma-Bellevue, WA | $747,400 | $482,755 | no | 32% | 9.4 years | 6.0 years | 1.0 years | beyond 30 years |
| Phoenix-Mesa-Chandler, AZ | $482,839 | $387,160 | no | 39% | 7.3 years | 4.0 years | 1.0 years | beyond 30 years |
| Miami-Fort Lauderdale-West Palm Beach, FL | $570,254 | $346,319 | no | 28% | 9.4 years | 3.0 years | 1.0 years | beyond 30 years |
| Riverside-San Bernardino-Ontario, CA | $601,161 | $390,940 | no | 29% | 9.4 years | 3.0 years | 1.0 years | beyond 30 years |
| Tampa-St. Petersburg-Clearwater, FL | $400,907 | $336,225 | no | 43% | 7.2 years | 3.0 years | 1.0 years | beyond 30 years |

| Line | Metros where the median household can afford the median home | Share | Note |
|---:|---:|---:|---|
| 25% | 119 | 31% |  |
| 28% | 191 | 50% | degenerate |
| 30% | 221 | 58% | chosen |
| 35% | 288 | 75% |  |

| Down payment | Median breakeven | Median down payment years | Note |
|---:|---:|---:|---|
| 5% | 11.0 years | 3.2 years |  |
| 10% | 9.5 years | 6.4 years | chosen |
| 20% | 8.0 years | 12.8 years |  |

| Saving rate | Median down payment years | Note |
|---:|---:|---|
| 5% | 12.8 years |  |
| 10% | 6.4 years | chosen |
| 15% | 4.3 years |  |

## The API

not yet deployed. Latency: live not measured; local not measured. Live check in a real browser: not checked (no browser yet, not yet; 0 of 0 routes; asleep: not observed).

## Limitations

- The dollar level of every price is the census median value in 2019 moved by the regulator index. Self reported values run high or low by metro (the census value over the transaction values in the loan extract has a median of 0.94x across 388 metros, from 0.81x to 1.04x), and the anchor carries that bias into every year; the sensitivity table bounds it.
- The payment is principal and interest on 30 year money with 10% down at the quarterly average rate; taxes, insurance and maintenance enter the breakeven and the workbook, not the headline share, so every share is understated by the same amount in every year.
- The census has no one year release for 2020; every series that crosses it breaks, and the borrower pool compares that year's loans with the prior year's incomes.
- The supply estimate is a lower bound in size: builders answer the price growth they are regressed on, and the simulator puts the attenuation at +0.0026 with the demand control and +0.0058 without it under its conditions. The migration series is one demand shock, not all of them.
- The migration regression's pre pandemic control removes most of the planted reverse causality on the simulator, where households move for one reason with one lag; the placebo flags the strong reverse causality condition in 46% of worlds, and remote work moved demand without moving many people.
- Intervals are cluster robust with 85 state clusters on the panel regressions, read on the t distribution with one fewer degree of freedom than clusters; with few clusters the recovery study, not the formula, is the evidence on coverage.
- The breakeven paths are drawn from each metro's own past, which includes a decade nobody expects to repeat; graded as late arriving truth on the simulator, the estimate missed the realised breakeven by 4.42 years on average.
- The lock in measure counts originations, so a metro whose owners refinanced twice at the bottom counts each refinance; the notebook keeps the version that counted refinances twice as a dead end, and turnover also fell because inventory fell.
- The check log stores a metro code, an income rounded to the nearest thousand, a down payment share, a rate and a horizon; it cannot say who asked, and the planted identifier scan proves nothing else is stored.
