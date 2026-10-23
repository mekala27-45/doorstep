# Definitions

> Public data from the Federal Housing Finance Agency, the Census Bureau (American Community Survey, Building Permits Survey, Population Estimates), the Department of Housing and Urban Development and the Consumer Financial Protection Bureau (HMDA), with mortgage rates from Freddie Mac under its terms of use. Metros are real and appear as they do in the public record; no household, borrower or address appears. The findings are a portfolio analysis, not financial advice, not a market forecast and not a fair lending finding.

A definition is a decision. Every term the story uses is defined once here, with the policy value it rests on, the code that computes it and the SQL the warehouse runs. Changing a value in `packages/core/src/doorstep_core/config.py` changes the plan hash of every chapter that uses it and fails the gate until the chapter is re-registered.

## The home and its price

- **The index.** The FHFA house price index for the metropolitan area: the purchase only, seasonally adjusted series where FHFA publishes it and the all transactions series otherwise, each use labeled in `mart_metro_quarter.index_source`. Where FHFA publishes metropolitan divisions, the divisions are rolled up to the area weighted by owner households through the delineation crosswalk (`int_fhfa_area`). 100 areas carry the purchase only index and 410 the all transactions index; 37 divisions are rolled up.
- **The median home (the anchored value).** The census median value of owner occupied units (table B25077) in the anchor year, 2019, moved forward and back by the index: `value_anchored = value_reported(anchor) * index / index(anchor)`. Code: `doorstep_chapters.panel.re_anchor`; warehouse column `mart_metro_year.value_anchored`. The sensitivity to anchoring in 2015, 2017, 2019 and 2023 is `ch1.anchor_sensitivity` on the data page; the headline is stable across them.
- **Price to income.** The anchored value over the median household income of the same metro and year (table B19013).

## The payment

- **The payment.** Principal and interest on a 30 year fixed rate mortgage for 10% down, at the quarterly average of the Freddie Mac thirty year rate (`mart_metro_quarter.rate`). Taxes and insurance are workbook inputs, not part of the headline. Code: `doorstep_finance.mortgage.payment`, tested against the closed form to the cent.
- **The payment share.** Twelve payments over the median household income. Code: `doorstep_finance.mortgage.payment_share`.
- **Affordable.** A payment share at or below 30%, the HUD standard, with 28% as the sensitivity and the interior test over 25%, 28%, 30% and 35%.
- **The affordable price.** The price whose payment share equals the line at the stated income, rate, down payment and term: the inverse of the payment share. Code: `doorstep_finance.mortgage.affordable_price`.
- **The affordable share.** The share of the metro's households whose income clears the payment on the median home at the line, interpolated inside the census income brackets (table B19001) with a Pareto top bracket. Code: `doorstep_finance.brackets`; graded against the exact share on the simulator (mean absolute error 0.4 pts).

## Renters and owners

- **Cost burdened, severely burdened.** Gross rent at or above 30% and 50% of household income, from table B25070, over renters with a computed share; by household income group from table B25074. Owners with a mortgage: selected monthly owner costs at or above the line, table B25091. Metric layer: `renter_burdened_share`.
- **The fair market rent and the area median income.** HUD's published values by area, joined through the HUD area map committed with its source (`data/hud_area_map.csv`), carried for context in the explorer.

## The loans

- **The extract.** Originated loans (action taken 1) for home purchase, refinance and cash out refinance (loan purposes 1, 31 and 32) on principal residences (occupancy type 1), 2018 to 2025. The fetch filter is `action_taken = 1 and loan_purpose in (1, 31, 32)`; the analysis filter is `occupancy_type = 1 (principal residence); reverse mortgages, open end lines and business purpose loans flagged`. The rounding rules are part of the contract: income in thousands, loan amount and property value at the midpoint of their reporting bins, age in bands. The derived race and ethnicity fields are not loaded.
- **The lock in intensity.** Originations in 2019 to 2021 with a rate under 4.00%, per hundred owner households of the metro (`mart_metro_year.low_rate_originations`); interior test over 3.0%, 3.5% and 4.0%. Code: `doorstep_loans.lock_in`.
- **Turnover.** Purchase originations per hundred owner households. Metric layer: `turnover_per_100_owners`.
- **The borrower income ratio.** The median purchase borrower income over the metro median household income of the nearest census year; **the under 35 share** is the share of purchase loans with a reported age band under 35. Code: `doorstep_chapters.c6_buyers`.

## Supply and people

- **Permits per hundred households.** Units permitted in the year (every structure size, county files mapped to the area through the vintage in force) per hundred households; the regressor of the supply chapter, shifted back one year. **Permits per new household** is published as a descriptive beside it and is undefined where households fell.
- **Domestic migration per hundred residents.** Net domestic migration from the population estimates over the population, by the July to June estimate year.

## The reader decision

- **The down payment years.** Years for a household at the renter median income to save 10% of the median home at a saving rate of 10% of income, with no return and no help; interior test over 5%, 10% and 15% and 5%, 10% and 20%.
- **The breakeven horizon.** The first year at which the cumulative cost of owning net of equity falls below the cumulative cost of renting with the down payment invested, under the cost model (closing costs 3.0% to buy and 6.0% to sell, property tax 1.1%, insurance 0.4%, maintenance 1.0% of value a year, mortgage insurance 0.6% under twenty percent down, an investment return of 4.5%), to a horizon of 30 years; appreciation and rent growth drawn by block bootstrap from the metro's own history. Code: `doorstep_finance.breakeven`.
- **A check and a score.** A check is one call to the calculator (metro, income rounded to the nearest thousand, down payment share, rate, horizon) with its answers and the carry forward expectation of next quarter's payment share; a score compares that expectation with the realised payment share once the next quarter of prices and rates publishes. Code: `doorstep_api.calculator`.

## The metric layer

Every metric is defined twice, over the finest grain and over the shipped mart, and `doorstep metrics` reconciles the two at 4 grains: 21 metrics, 1,764 cells, 0 disagreements.

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
