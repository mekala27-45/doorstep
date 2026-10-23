# Can anyone still afford a home: the briefing

*doorstep, as of 2026-10-22. 60 metropolitan areas present in both the regulator price index and the one year census release; prices and rates from 1975 to 2026Q2, census releases from 2005 to 2024, mortgage originations from 2018 to 2024. Chapters that fit anything choose on 2005 to 2019 and report from 2021. Every figure is rendered from the analysis manifest.*

> Public data from the Federal Housing Finance Agency, the Census Bureau (American Community Survey, Building Permits Survey, Population Estimates), the Department of Housing and Urban Development and the Consumer Financial Protection Bureau (HMDA), with mortgage rates from Freddie Mac under its terms of use. Metros are real and appear as they do in the public record; no household, borrower or address appears. The findings are a portfolio analysis, not financial advice, not a market forecast and not a fair lending finding.

## The eight findings

- **The payment story happened in eighteen months while the price story took twenty years: the share of income the median home takes in 2024 sits +2.6 pts above 2006 (interval +2.4 pts to +2.8 pts).** The payment share of the median home is 26.8% in 2024 (26.6% to 27.0%), +2.6 pts against the 2006 peak, while price to income moved +3.6% over the whole span.
- **The rate part of the payment overtook the price part in 2022Q3. The lock in coefficient (-0.02, interval -0.13 to +0.10) cannot be told from zero.** The rate part is 57% of the payment change since 2019Q1; each point of lock in moved turnover by -0.019 (-0.132 to +0.095) against a placebo of +0.046.
- **The median renter is burdened in most metros (100% of them) in 2024; the problem is the whole distribution, with 32.5% of renters paying half or more. The national series moved and stayed moved in 2009, 2013, 2018, 2022.** 32.5% of renters pay half or more of income in rent (29.3% to 36.3%); the national severe series broke in 2009, 2013, 2018, 2022.
- **Where builders kept pace, prices rose less: 10.7% less price growth over 5 years per extra permit per hundred households (interval -13.8% to -7.6%); without the demand control the estimate is -8.3%.** -10.7% price growth per window per extra permit per hundred households with the demand control (-13.8% to -7.6%); -8.3% without it.
- **The ranking changes when you hold constant what people earn there: 10 of the 20 largest metros move beyond their intervals. Less affordable than their price says: Simulated metro 38 from 37 to 18; Simulated metro 53 from 35 to 23; Simulated metro 12 from 31 to 20. More affordable: Simulated metro 46 from 4 to 15; Simulated metro 15 from 39 to 49; Simulated metro 23 from 33 to 37.** Rank correlation 0.90 between the price ranking and the payment share ranking; the largest move is Simulated metro 59, from 18 to 47.
- **The buyer is richer than in 2019 by +0.09 of the local median income (interval +0.08 to +0.10), but not measurably older: the under 35 share moved -0.2 pts with an interval that includes zero. The ratio moved most in Simulated metro 12 +0.20; Simulated metro 33 +0.17; Simulated metro 56 +0.15.** The median purchase borrower earns 1.43x the local median income in 2024 against 1.35x in 2019; the under thirty five share moved -0.2 pts.
- **Demand moved and prices followed: +1.5% price growth over the window per person gained per hundred residents beyond the pre pandemic pace (interval +1.2% to +1.9%), with a placebo of 0.0% on the years before the pandemic whose interval includes zero.** +1.54% price growth per person gained per hundred residents (+1.23% to +1.86%), placebo -0.04% (-0.48% to +0.41%).
- **Buying beats renting only after 15.0 years in the typical metro (interval 2.0 years to beyond 30 years), and one point of rate moves the breakeven by +5.5 years. Longest to break even among the largest metros: Simulated metro 29 beyond 30 years; Simulated metro 14 beyond 30 years; Simulated metro 47 beyond 30 years.** Median breakeven 15.0 years (2.0 years to beyond 30 years); the median household can afford the median home in 37 of 60 metros; 6.1 years to the down payment in the typical metro.

## 1. Affordable is a decision

<!-- chart: definition -->
**The payment story happened in eighteen months while the price story took twenty years: the share of income the median home takes in 2024 sits +2.6 pts above 2006 (interval +2.4 pts to +2.8 pts).** Price to income for the owner weighted aggregate of 60 metros went from 3.6x in 2005 to 3.8x in 2024 (+3.6%), with the cycle peak at 3.7x in 2006. The payment share, twelve payments on the median home at the rate of each quarter over the median income, went from 24.1% to 26.8% (26.6% to 27.0%), +2.6 pts against the peak (+2.4 pts to +2.8 pts). 47 metros (78%) sit above their own peak payment share; 23 (38%) sit above the 30% line.

| Anchor year | Latest payment share | 2006 payment share | Difference | Metros above 2006 | Note |
|---:|---:|---:|---:|---:|---|
| 2,015 | 26.9% | 24.3% | +2.6 pts | 47 |  |
| 2,017 | 26.7% | 24.1% | +2.6 pts | 47 |  |
| 2,019 | 26.8% | 24.2% | +2.6 pts | 47 | chosen |
| 2,023 | 26.6% | 24.0% | +2.6 pts | 47 |  |

**Method.** Plan `ac7975b9fb0c601f`; the anchored index with the payment at the quarterly rate; 2000 Monte Carlo draws over the census margins of error, index held fixed; no fitted parameter; the baseline years are 2005 to 2019 and the headline is the latest release. Anchor sensitivity: stable. Simulator: anchored payment share mean bias -0.02 pts; self report correction mean bias -0.002.

### What the housing economist would push back on

Self reported values run high or low by metro, and the anchor carries that bias into every year. The anchor sensitivity table shows what moving the anchor year does to the headline, and the self report check prints the census value over the transaction values in the loan extract for the same year; neither removes the bias, they bound it. The payment is principal and interest only, so a reader who adds taxes and insurance will find every share here understated by the same amount in every year.

## 2. The rate shock and the lock in

<!-- chart: rate_shock -->
**The rate part of the payment overtook the price part in 2022Q3. The lock in coefficient (-0.02, interval -0.13 to +0.10) cannot be told from zero.** The payment on the home as priced in 2019Q1 went from $1,208 to $2,191 by 2024Q4 (+$983): +$424 from the price and +$559 from the rate, 57% of the change, which overtook the price part in 2022Q3. Lock in intensity (1.7 million originations under 4.00% in 2019 to 2021, per hundred owner households) runs from 10.4 to 11.7 across metros; turnover fell from 1.63 to 1.17; the regression gives -0.019 per point (-0.132 to +0.095) against a placebo of +0.046 (-0.025 to +0.117).

| Threshold | Coefficient | Low | High | Placebo | Note |
|---:|---:|---:|---:|---:|---|
| 3.00% | -0.023 | -0.275 | +0.229 | +0.085 |  |
| 3.50% | -0.016 | -0.152 | +0.121 | +0.050 |  |
| 4.00% | -0.019 | -0.132 | +0.095 | +0.046 | chosen |

**Method.** Plan `dc55265cae0a0e21`; exact price and rate decomposition of the payment; turnover on lock in intensity with metro and year fixed effects on owner weighted cells; cluster robust by state, 9 clusters; event window 2019 to the latest quarter; base years 2018 and 2019; test years from 2023; 240 cells. Threshold interior: stable. Simulator: lock in mean bias +0.0015, coverage 94%.

### What the housing economist would push back on

Lock in is measured from originations, so a metro where owners refinanced twice at the bottom counts each refinance; the measure is an intensity, not a count of owners, and the notebook keeps the version that counted refinances twice as a dead end. Turnover also fell because inventory fell, and a metro with little inventory sees fewer purchases whatever its owners hold; the placebo bounds the trend, it does not remove the mechanism.

## 3. The rent burden is a distribution

<!-- chart: burden -->
**The median renter is burdened in most metros (100% of them) in 2024; the problem is the whole distribution, with 32.5% of renters paying half or more. The national series moved and stayed moved in 2009, 2013, 2018, 2022.** 57.8% of renter households pay 30% or more of income in rent (54.0% to 61.8%) and 32.5% pay 50% or more (29.3% to 36.3%) in 2024; the median renter is under the line in 0 of 60 metros. Nationally the severe share went from 28.1% to 32.5% (+4.4 pts) with breaks in 2009, 2013, 2018, 2022. Owners with a mortgage: 28.0% burdened.

| Income group | Renters | Burdened | Severely burdened |
|---|---:|---:|---:|
| under 10k | 682,620 | 95.0% | 75.0% |
| 10k to 20k | 1,450,567 | 85.0% | 50.0% |
| 20k to 35k | 1,877,204 | 60.0% | 25.0% |
| 35k to 50k | 1,450,567 | 35.0% | 8.0% |
| 50k to 75k | 1,535,894 | 15.0% | 2.0% |
| 75k to 100k | 767,947 | 5.0% | 0.0% |
| 100k plus | 767,947 | 2.0% | 0.0% |

**Method.** Plan `a2850a134d98e2a1`; burdened and severely burdened renters over renters with a computed share; PELT with a BIC penalty on the national series; block bootstrap over metros, 200 replicates; census ratio margins per metro. Severe line interior: stable. Simulator: severe share mean bias 0.00 pts; changepoint within a year of the planted step in 100% of worlds.

### What the housing economist would push back on

Gross rent as a share of income is computed only for renters who reported both, and the census excludes those it could not compute; a metro where many students or retirees rent shows a high severe share that is income, not rent. The bands are left closed at thirty and fifty percent because the census publishes them that way, and a household at 29.9 percent is counted as unburdened by a line it did not choose.

## 4. Supply

<!-- chart: supply -->
**Where builders kept pace, prices rose less: 10.7% less price growth over 5 years per extra permit per hundred households (interval -13.8% to -7.6%); without the demand control the estimate is -8.3%.** 180 metro by window cells over 3 windows of 5 years; the building rate runs from 0.60 to 1.89 permits per hundred households. With the demand control: -10.7% per window per extra permit (-13.8% to -7.6%); without: -8.3% (-12.1% to -4.5%). Between the tenth and ninetieth percentile building rate: -13.8% over a window.

| Specification | Annual growth per permit per 100 households | Low | High | Over the window | Clusters |
|---|---:|---:|---:|---:|---:|
| with the demand control | -0.0215 | -0.0277 | -0.0153 | -10.7% | 9 |
| without the demand control | -0.0166 | -0.0242 | -0.0091 | -8.3% | 9 |

**Method.** Plan `a1d050c1b22c5986`; fixed effects on population weighted metro by window cells, alternating projections, two specifications; cluster robust by state, 9 clusters; non overlapping 5 year windows from 2006; permits shifted back one year. Window interior: stable. Simulator (truth -0.025): controlled mean bias +0.0026, uncontrolled +0.0058; under strong demand +0.0031 against +0.0078.

### What the housing economist would push back on

Permits respond to demand: a metro builds because prices are rising, which pushes the uncontrolled estimate toward zero or past it, and the recovery study measures that bias under every condition. The migration series is one demand shock, not all of them; income growth and investor demand are not in the regression. Permits are not completions, and a permit pulled in a downturn may never become a home. The notebook keeps the specification that put the demand shock in the wrong fixed effect as a dead end.

## 5. The fair ranking

<!-- chart: ranking -->
**The ranking changes when you hold constant what people earn there: 10 of the 20 largest metros move beyond their intervals. Less affordable than their price says: Simulated metro 38 from 37 to 18; Simulated metro 53 from 35 to 23; Simulated metro 12 from 31 to 20. More affordable: Simulated metro 46 from 4 to 15; Simulated metro 15 from 39 to 49; Simulated metro 23 from 33 to 37.** 60 metropolitan areas ranked in 2024 by the anchored median value and by the payment share at the local median income, with rank intervals from 2,000 Monte Carlo draws over the census margins. Most expensive: Simulated metro 1; Simulated metro 30; Simulated metro 43. Least affordable: Simulated metro 1; Simulated metro 5; Simulated metro 43, led by Simulated metro 1 at 49.9% (46.8% to 53.5%). Rank correlation 0.90; mean rank change 5.4 places; largest 29 (Simulated metro 59). Affordable share from 16% to 80%, median 55%.

| Metro | Households | Median home | Median income | Payment share | Low | High | Raw rank | Adjusted rank | Interval | Moves |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| Simulated metro 41 | 557,235 | $642,747 | $129,949 | 35.1% | 33.5% | 36.7% | 7 | 7 | 5 to 14 | no |
| Simulated metro 57 | 727,854 | $526,629 | $108,026 | 34.6% | 33.1% | 36.1% | 14 | 11 | 6 to 15 | no |
| Simulated metro 32 | 377,166 | $623,129 | $129,541 | 34.1% | 32.5% | 35.9% | 9 | 13 | 6 to 15 | no |
| Simulated metro 46 | 474,447 | $686,358 | $144,024 | 33.8% | 32.3% | 35.3% | 4 | 15 | 8 to 16 | yes |
| Simulated metro 38 | 594,461 | $311,358 | $70,375 | 31.4% | 30.1% | 32.9% | 37 | 18 | 15 to 23 | yes |
| Simulated metro 12 | 988,062 | $354,255 | $81,346 | 30.9% | 29.6% | 32.3% | 31 | 20 | 16 to 24 | yes |
| Simulated metro 53 | 1,162,044 | $321,217 | $75,456 | 30.2% | 28.9% | 31.6% | 35 | 23 | 18 to 27 | yes |
| Simulated metro 29 | 2,415,629 | $433,797 | $106,051 | 29.0% | 28.0% | 30.1% | 23 | 26 | 22 to 30 | no |
| Simulated metro 56 | 1,200,110 | $426,732 | $105,511 | 28.7% | 27.4% | 29.9% | 24 | 28 | 23 to 32 | no |
| Simulated metro 33 | 940,395 | $367,828 | $94,900 | 27.5% | 26.3% | 28.7% | 29 | 32 | 27 to 33 | no |
| Simulated metro 6 | 389,663 | $306,824 | $80,806 | 26.9% | 25.8% | 28.2% | 38 | 33 | 30 to 34 | yes |
| Simulated metro 14 | 845,635 | $277,225 | $77,900 | 25.2% | 24.2% | 26.4% | 45 | 35 | 34 to 40 | yes |
| Simulated metro 23 | 608,212 | $341,824 | $98,773 | 24.6% | 23.4% | 25.7% | 33 | 37 | 35 to 44 | yes |
| Simulated metro 4 | 1,065,271 | $291,652 | $86,216 | 24.0% | 23.0% | 25.0% | 42 | 41 | 36 to 45 | no |
| Simulated metro 15 | 457,833 | $304,452 | $99,837 | 21.6% | 20.6% | 22.7% | 39 | 49 | 46 to 51 | yes |
| Simulated metro 48 | 937,869 | $240,403 | $80,738 | 21.1% | 20.3% | 22.0% | 50 | 50 | 48 to 52 | no |
| Simulated metro 13 | 423,046 | $201,536 | $67,737 | 21.1% | 20.2% | 22.0% | 54 | 51 | 48 to 52 | yes |
| Simulated metro 39 | 906,168 | $221,898 | $76,278 | 20.6% | 19.8% | 21.5% | 52 | 52 | 49 to 52 | no |
| Simulated metro 47 | 747,488 | $198,531 | $84,053 | 16.8% | 16.0% | 17.6% | 55 | 57 | 56 to 60 | yes |
| Simulated metro 35 | 988,391 | $133,428 | $59,311 | 16.0% | 15.3% | 16.6% | 60 | 60 | 58 to 60 | no |

**Method.** Plan `e23fc6df73f96272`; payment share at the local median income; affordable share by bracket interpolation; 2000 Monte Carlo draws over the income and anchor value margins, index held fixed. Simulator: adjusted ranking rank correlation with the truth 0.956 against 0.890 for the price ranking; bracket interpolation mean absolute error 0.4 pts.

### What the housing economist would push back on

The median income is not the buyer income: in a metro where buyers earn twice the median, the payment share of the median household overstates what the people who actually buy face, and chapter 6 measures that ratio from the loans. The index has no margin, so the interval understates what a thin market's index carries. Metros that lost their one year census coverage drop out of the ranking in that year rather than being carried.

## 6. Who still buys

<!-- chart: buyers -->
**The buyer is richer than in 2019 by +0.09 of the local median income (interval +0.08 to +0.10), but not measurably older: the under 35 share moved -0.2 pts with an interval that includes zero. The ratio moved most in Simulated metro 12 +0.20; Simulated metro 33 +0.17; Simulated metro 56 +0.15.** From 251,037 purchase originations in 2019 and 189,323 in 2024: borrower income over the metro median 1.35x to 1.43x (+0.09, +0.08 to +0.10); share earning over twice the median 18.8% to 22.5%; under thirty five share 34.1% to 33.9% (-0.2 pts, -0.5 pts to +0.1 pts); value to income 2.62x to 2.62x; median rate spread 0.31%.

| Year | Loans | Lenders | Income ratio | Low | High | Under 35 | Above twice the median | Value to income | Spread p50 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2,018 | 244,600 | 40 | 1.35x | 1.35x | 1.35x | 34.0% | 19.0% | 2.62x | 0.31% |
| 2,019 | 251,037 | 40 | 1.35x | 1.34x | 1.35x | 34.1% | 18.8% | 2.62x | 0.31% |
| 2,020 | 249,883 | 40 | 1.40x | 1.40x | 1.41x | 34.1% | 21.5% | 2.62x | 0.31% |
| 2,021 | 251,458 | 40 | 1.34x | 1.33x | 1.35x | 33.9% | 18.6% | 2.62x | 0.31% |
| 2,022 | 257,943 | 40 | 1.36x | 1.35x | 1.36x | 33.8% | 19.5% | 2.88x | 0.31% |
| 2,023 | 181,989 | 40 | 1.44x | 1.44x | 1.44x | 34.0% | 23.2% | 2.62x | 0.31% |
| 2,024 | 189,323 | 40 | 1.43x | 1.43x | 1.44x | 33.9% | 22.5% | 2.62x | 0.31% |

**Method.** Plan `fa89aa88427acdac`; weighted medians over five thousand dollar income bins per lender; shares as ratios of sums; bootstrap over lenders within year, 200 replicates; base year 2019; reported on 2024. Simulator: ratio shift mean bias -0.001; under thirty five shift -0.02 pts.

### What the housing economist would push back on

The HMDA income is the income the lender used, not the household's; a co-borrower or a self employed buyer is reported differently by different lenders, which is why the interval resamples lenders. The ratio compares buyers with the metro median household in the nearest census year, and the census has no 2020 release, so 2020 loans are compared with 2019 incomes. The purchase subset leaves out buyers who paid cash, who are the richest buyers of all.

## 7. The migration shock

<!-- chart: migration -->
**Demand moved and prices followed: +1.5% price growth over the window per person gained per hundred residents beyond the pre pandemic pace (interval +1.2% to +1.9%), with a placebo of 0.0% on the years before the pandemic whose interval includes zero.** Across 60 metros, price growth over 2019Q4 to 2021Q4 on the migration shock (per hundred residents, 2020 and 2021 less 2018 and 2019): +1.54% per person (+1.23% to +1.86%); placebo on 2016Q4 to 2018Q4: -0.04% (-0.48% to +0.41%); level alone with no control: +0.96%. Synthetic controls for Simulated metro 37; Simulated metro 26; Simulated metro 40: peak gaps +3.8%, +7.9% and +2.1%; latest gaps -2.6%, +7.9% and -3.3%; permutation p values 0.774, 0.355 and 0.839.

| Window | Growth per person per 100 residents of shock | Low | High | p | Clusters |
|---|---:|---:|---:|---:|---:|
| 2019Q4 to 2021Q4 | +1.54% | +1.23% | +1.86% | 0.000 | 9 |
| 2016Q4 to 2018Q4 (placebo) | -0.04% | -0.48% | +0.41% | 0.855 | 9 |
| 2019Q4 to 2021Q4 (level alone, no pre pandemic control) | +0.96% | +0.71% | +1.21% | 0.000 | 9 |

**Method.** Plan `b2cbe5f6a4559c90`; cross section of metros on the migration shock with the pre pandemic migration as a control, one observation per metro, state clusters; synthetic control on the simplex with every donor searched; cluster robust by state, 9 clusters; permutation p values over 30 donors; window 2019Q4 to 2021Q4; placebo 2016Q4 to 2018Q4. Simulator: controlled estimate mean bias -0.02%, coverage 98%; level alone -0.30% with no reverse causality and -0.51% under strong; placebo flag rate 46% under strong reverse causality against 6% under none.

### What the housing economist would push back on

Migration follows affordability: people move to the metros they can afford, and a metro that was already cheap for its incomes was already on a different price path. On the simulator the regression on the migration level alone carries that bias and the pre pandemic control removes most of it, but the simulator's households move for one reason with one lag, and the placebo flags the planted reverse causality only part of the time; that is the limit this chapter admits in print. The population estimates count domestic migration from July to June, so the migration years and the price window overlap by two quarters and not four. Remote work moved demand without moving many people, and that part is not in the migration series.

## 8. The reader decision

<!-- chart: decision -->
**Buying beats renting only after 15.0 years in the typical metro (interval 2.0 years to beyond 30 years), and one point of rate moves the breakeven by +5.5 years. Longest to break even among the largest metros: Simulated metro 29 beyond 30 years; Simulated metro 14 beyond 30 years; Simulated metro 47 beyond 30 years.** At the 30% line, 10% down and 6.88%, the median household can afford the median home in 37 of 60 metros (62%); median affordable share 55%; down payment years 6.1 years in the typical metro, 11.4 years in Simulated metro 1. Owner weighted median breakeven 15.0 years (2.0 years to beyond 30 years); 36% of paths never break even inside 30 years; one point of rate moves the breakeven by +5.5 years. Quickest: Simulated metro 15 (3 years); slowest: Simulated metro 29 (beyond 30 years).

| Metro | Median home | Affordable price | Can afford | Affordable share | Down payment years | Breakeven | Low | High |
|---|---:|---:|---|---:|---:|---:|---:|---:|
| Simulated metro 29 | $433,797 | $448,429 | yes | 52% | 6.5 years | beyond 30 years | beyond 30 years | beyond 30 years |
| Simulated metro 14 | $277,225 | $329,393 | yes | 61% | 5.5 years | beyond 30 years | 10.0 years | beyond 30 years |
| Simulated metro 47 | $198,531 | $355,412 | yes | 80% | 3.7 years | beyond 30 years | 2.0 years | beyond 30 years |
| Simulated metro 23 | $341,824 | $417,653 | yes | 61% | 5.4 years | beyond 30 years | 2.0 years | beyond 30 years |
| Simulated metro 38 | $311,358 | $297,574 | no | 48% | 6.9 years | beyond 30 years | 3.0 years | beyond 30 years |
| Simulated metro 41 | $642,747 | $549,479 | no | 43% | 7.5 years | beyond 30 years | 9.0 years | beyond 30 years |
| Simulated metro 12 | $354,255 | $343,967 | no | 50% | 6.7 years | 24.0 years | 2.0 years | beyond 30 years |
| Simulated metro 35 | $133,428 | $250,791 | yes | 80% | 3.5 years | 22.5 years | 2.0 years | beyond 30 years |
| Simulated metro 13 | $201,536 | $286,421 | yes | 68% | 4.6 years | 15.5 years | 2.0 years | beyond 30 years |
| Simulated metro 33 | $367,828 | $401,277 | yes | 55% | 6.1 years | 15.0 years | 2.0 years | beyond 30 years |
| Simulated metro 57 | $526,629 | $456,779 | no | 42% | 7.6 years | 15.0 years | 3.0 years | beyond 30 years |
| Simulated metro 32 | $623,129 | $547,754 | no | 44% | 7.5 years | 13.0 years | 3.0 years | beyond 30 years |
| Simulated metro 56 | $426,732 | $446,145 | yes | 53% | 6.3 years | 11.5 years | 4.0 years | beyond 30 years |
| Simulated metro 4 | $291,652 | $364,560 | yes | 61% | 5.3 years | 11.0 years | 4.0 years | beyond 30 years |
| Simulated metro 53 | $321,217 | $319,061 | no | 51% | 6.5 years | 9.0 years | 2.0 years | 25.0 years |
| Simulated metro 39 | $221,898 | $322,538 | yes | 71% | 4.6 years | 7.0 years | 2.0 years | 20.0 years |
| Simulated metro 48 | $240,403 | $341,393 | yes | 69% | 4.5 years | 6.0 years | 2.0 years | 15.0 years |
| Simulated metro 46 | $686,358 | $608,995 | no | 43% | 7.6 years | 6.0 years | 2.0 years | 26.1 years |
| Simulated metro 6 | $306,824 | $341,683 | yes | 55% | 6.0 years | 6.0 years | 2.0 years | 18.1 years |
| Simulated metro 15 | $304,452 | $422,155 | yes | 70% | 4.7 years | 3.0 years | 2.0 years | 28.0 years |

**Method.** Plan `10988e362f89ee23`; closed form payment arithmetic; bracket interpolation; breakeven under the cost model on bootstrap paths; block bootstrap, blocks of 3 years, 200 paths per metro; paths from each metro's own history; reported in 2024 at the latest quarterly rate. Interior tests: line degenerate, down payment stable. Simulator, late arriving truth: mean error 4.42 years, interval coverage 70%.

### What the housing economist would push back on

A payment is not the whole cost of owning: the cost model adds taxes, insurance, maintenance and the costs of buying and selling, but not the roof that fails in year four, and it credits the renter with a return the renter has to earn. The paths are drawn from the metro's own past, which includes a decade nobody expects to repeat, and the interval is the spread of those paths, not a forecast. The down payment years assume a renter who saves a tenth of income with no help and no return, which is the simplest honest reading of the question.

## Limitations

- The dollar level of every price is the census median value in 2019 moved by the regulator index; self reported values run high or low by metro and the anchor carries that bias into every year. The anchor sensitivity table bounds it; nothing here removes it.
- The payment is principal and interest on 30 year money with 10% down; taxes, insurance and maintenance enter the breakeven and the workbook, not the headline share.
- The one year census release does not exist for 2020; every series that crosses it breaks, and the borrower pool compares that year's loans with the prior year's incomes.
- The supply estimate is a lower bound in size: builders answer the price growth they are regressed on, and the simulator puts the resulting attenuation at +0.0026 with the demand control under its conditions.
- The migration regression's control removes most of the planted reverse causality on the simulator, but the simulator's households move for one reason with one lag; the placebo flags the strong reverse causality condition in 46% of worlds.
- The breakeven paths are drawn from each metro's own past, which includes a decade nobody expects to repeat; graded as late arriving truth on the simulator the estimate missed the realised breakeven by 4.42 years on average because the simulated decade held a boom the history did not.
- The check log stores a metro code, an income rounded to the nearest thousand, a down payment share, a rate and a horizon; it cannot say who asked.

### What the housing economist would push back on

Every number here rests on a definition this build chose and stated: the anchor year, the 30% line, 10% down, the cost model. The interior tests print each headline under the neighbours of those choices and the word degenerate where the headline turns at the first one; the economist would start there, and so should the reader.
