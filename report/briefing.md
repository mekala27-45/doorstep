# Can anyone still afford a home: the briefing

*doorstep, as of 2026-10-23. 393 metropolitan areas present in both the regulator price index and the one year census release; prices and rates from 1975 to 2026Q2, census releases from 2005 to 2024, mortgage originations from 2018 to 2025. Chapters that fit anything choose on 2005 to 2019 and report from 2021. Every figure is rendered from the analysis manifest.*

> Public data from the Federal Housing Finance Agency, the Census Bureau (American Community Survey, Building Permits Survey, Population Estimates), the Department of Housing and Urban Development and the Consumer Financial Protection Bureau (HMDA), with mortgage rates from Freddie Mac under its terms of use. Metros are real and appear as they do in the public record; no household, borrower or address appears. The findings are a portfolio analysis, not financial advice, not a market forecast and not a fair lending finding.

## The eight findings

- **The payment share of 2024 does not exceed 2023; the payment story is not yet the largest the window has seen. It sits +1.1 pts above 2006 (interval +1.0 pts to +1.3 pts), so the 2006 peak is passed, and the window's own peak is 2023.** The payment share of the median home is 34.9% in 2024 (34.8% to 35.0%), +1.1 pts against the 2006 peak, while price to income moved +3.4% over the whole span.
- **The rate part of the payment overtook the price part in 2023Q3. The rate shock froze turnover where owners had the most to lose: 0.06 fewer purchases per 100 owner households per point of lock in (interval -0.08 to -0.03), and the placebo on the years before the shock sits at 0.00 with an interval that includes zero.** The rate part is 40% of the payment change since 2019Q1; each point of lock in moved turnover by -0.056 (-0.077 to -0.034) against a placebo of +0.001.
- **The median renter is burdened in 51% of metros in 2024, so the median hides nothing; the problem is the whole distribution, with 26.5% of renters paying half or more (interval 25.7% to 27.2%). The national series moved and stayed moved in 2009, 2015, 2021.** 26.5% of renters pay half or more of income in rent (25.7% to 27.2%); the national severe series broke in 2009, 2015, 2021.
- **Where builders kept pace, prices rose less: 8.0% less price growth over 5 years per extra permit per hundred households (interval -14.3% to -1.7%); without the demand control the estimate is -0.4%.** -8.0% price growth per window per extra permit per hundred households with the demand control (-14.3% to -1.7%); -0.4% without it.
- **The ranking changes when you hold constant what people earn there: 17 of the 20 largest metros move beyond their intervals. Less affordable than their price says: Tampa-St. Petersburg-Clearwater from 106 to 90; Miami-Fort Lauderdale-West Palm Beach from 33 to 22; Los Angeles-Long Beach-Anaheim from 7 to 2. More affordable: St. Louis from 223 to 307; Minneapolis-St. Paul-Bloomington from 114 to 195; Washington-Arlington-Alexandria from 25 to 102.** Rank correlation 0.94 between the price ranking and the payment share ranking; the largest move is Lexington Park, MD, from 72 to 243.
- **The buyer is richer than in 2019 by +0.15 of the local median income (interval +0.12 to +0.19) and, against the claim, slightly younger: the under 35 share rose +1.2 pts (interval +0.1 pts to +2.3 pts) by 2025. The ratio moved most in Los Angeles-Long Beach-Anaheim +0.44; Miami-Fort Lauderdale-West Palm Beach +0.37; New York-Newark-Jersey City +0.30.** The median purchase borrower earns 1.39x the local median income in 2025 against 1.23x in 2019; the under thirty five share moved +1.2 pts.
- **The metros that gained people were already lagging before the pandemic: the placebo on the years before it is -0.8% (interval -1.4% to -0.2%), so the headline of +1.5% price growth over the window per person gained per hundred residents beyond the pre pandemic pace is a lower bound on what the migration itself did.** +1.48% price growth per person gained per hundred residents (+0.40% to +2.55%), placebo -0.78% (-1.35% to -0.20%).
- **Buying beats renting only after 10.0 years in the typical metro (interval 1.0 years to beyond 30 years), and one point of rate moves the breakeven by +4.5 years. Longest to break even among the largest metros: Boston-Cambridge-Newton 21 years; Chicago-Naperville-Elgin 20 years; San Francisco-Oakland-Fremont 18 years.** Median breakeven 10.0 years (1.0 years to beyond 30 years); the median household can afford the median home in 221 of 382 metros; 6.4 years to the down payment in the typical metro.

## 1. Affordable is a decision

<!-- chart: definition -->
**The payment share of 2024 does not exceed 2023; the payment story is not yet the largest the window has seen. It sits +1.1 pts above 2006 (interval +1.0 pts to +1.3 pts), so the 2006 peak is passed, and the window's own peak is 2023.** Price to income for the owner weighted aggregate of 375 metros went from 4.8x in 2005 to 5.0x in 2024 (+3.4%), with the cycle peak at 5.0x in 2006. The payment share, twelve payments on the median home at the rate of each quarter over the median income, went from 30.8% to 34.9% (34.8% to 35.0%), +1.1 pts against the peak (+1.0 pts to +1.3 pts). 283 metros (75%) sit above their own peak payment share; 161 (42%) sit above the 30% line.

| Anchor year | Latest payment share | 2006 payment share | Difference | Metros above 2006 | Note |
|---:|---:|---:|---:|---:|---|
| 2,015 | 35.0% | 33.8% | +1.1 pts | 283 |  |
| 2,017 | 34.8% | 33.7% | +1.1 pts | 283 |  |
| 2,019 | 34.9% | 33.7% | +1.1 pts | 283 | chosen |
| 2,023 | 33.5% | 32.3% | +1.2 pts | 283 |  |

**Method.** Plan `ac7975b9fb0c601f`; the anchored index with the payment at the quarterly rate; 2000 Monte Carlo draws over the census margins of error, index held fixed; no fitted parameter; the baseline years are 2005 to 2019 and the headline is the latest release. Anchor sensitivity: stable. Simulator: anchored payment share mean bias -0.02 pts; self report correction mean bias -0.002.

### What the housing economist would push back on

Self reported values run high or low by metro, and the anchor carries that bias into every year. The anchor sensitivity table shows what moving the anchor year does to the headline, and the self report check prints the census value over the transaction values in the loan extract for the same year; neither removes the bias, they bound it. The payment is principal and interest only, so a reader who adds taxes and insurance will find every share here understated by the same amount in every year.

## 2. The rate shock and the lock in

<!-- chart: rate_shock -->
**The rate part of the payment overtook the price part in 2023Q3. The rate shock froze turnover where owners had the most to lose: 0.06 fewer purchases per 100 owner households per point of lock in (interval -0.08 to -0.03), and the placebo on the years before the shock sits at 0.00 with an interval that includes zero.** The payment on the home as priced in 2019Q1 went from $1,316 to $2,704 by 2026Q2 (+$1,388): +$839 from the price and +$549 from the rate, 40% of the change, which overtook the price part in 2023Q3. Lock in intensity (18.4 million originations under 4.00% in 2019 to 2021, per hundred owner households) runs from 10.7 to 36.6 across metros; turnover fell from 5.28 to 3.71; the regression gives -0.056 per point (-0.077 to -0.034) against a placebo of +0.001 (-0.002 to +0.004).

| Threshold | Coefficient | Low | High | Placebo | Note |
|---:|---:|---:|---:|---:|---|
| 3.00% | -0.094 | -0.146 | -0.042 | +0.001 |  |
| 3.50% | -0.067 | -0.096 | -0.038 | +0.001 |  |
| 4.00% | -0.056 | -0.077 | -0.034 | +0.001 | chosen |

**Method.** Plan `dc55265cae0a0e21`; exact price and rate decomposition of the payment; turnover on lock in intensity with metro and year fixed effects on owner weighted cells; cluster robust by state, 86 clusters; event window 2019 to the latest quarter; base years 2018 and 2019; test years from 2023; 1,549 cells. Threshold interior: stable. Simulator: lock in mean bias +0.0015, coverage 94%.

### What the housing economist would push back on

Lock in is measured from originations, so a metro where owners refinanced twice at the bottom counts each refinance; the measure is an intensity, not a count of owners, and the notebook keeps the version that counted refinances twice as a dead end. Turnover also fell because inventory fell, and a metro with little inventory sees fewer purchases whatever its owners hold; the placebo bounds the trend, it does not remove the mechanism.

## 3. The rent burden is a distribution

<!-- chart: burden -->
**The median renter is burdened in 51% of metros in 2024, so the median hides nothing; the problem is the whole distribution, with 26.5% of renters paying half or more (interval 25.7% to 27.2%). The national series moved and stayed moved in 2009, 2015, 2021.** 52.5% of renter households pay 30% or more of income in rent (51.5% to 53.5%) and 26.5% pay 50% or more (25.7% to 27.2%) in 2024; the median renter is under the line in 193 of 392 metros. Nationally the severe share went from 25.1% to 26.1% (+0.9 pts) with breaks in 2009, 2015, 2021. Owners with a mortgage: 30.9% burdened.

| Income group | Renters | Burdened | Severely burdened |
|---|---:|---:|---:|
| under 10k | 2,100,866 | 97.8% | 93.5% |
| 10k to 20k | 3,318,512 | 86.6% | 70.5% |
| 20k to 35k | 4,575,863 | 88.3% | 59.8% |
| 35k to 50k | 4,532,267 | 78.0% | 30.8% |
| 50k to 75k | 6,509,505 | 56.1% | 10.3% |
| 75k to 100k | 4,512,280 | 30.6% | 3.2% |
| 100k plus | 9,407,120 | 9.7% | 0.9% |

**Method.** Plan `a2850a134d98e2a1`; burdened and severely burdened renters over renters with a computed share; PELT with a BIC penalty on the national series; block bootstrap over metros, 400 replicates; census ratio margins per metro. Severe line interior: stable. Simulator: severe share mean bias 0.00 pts; changepoint within a year of the planted step in 100% of worlds.

### What the housing economist would push back on

Gross rent as a share of income is computed only for renters who reported both, and the census excludes those it could not compute; a metro where many students or retirees rent shows a high severe share that is income, not rent. The bands are left closed at thirty and fifty percent because the census publishes them that way, and a household at 29.9 percent is counted as unburdened by a line it did not choose.

## 4. Supply

<!-- chart: supply -->
**Where builders kept pace, prices rose less: 8.0% less price growth over 5 years per extra permit per hundred households (interval -14.3% to -1.7%); without the demand control the estimate is -0.4%.** 1,925 metro by window cells over 5 windows of 5 years; the building rate runs from 0.34 to 2.55 permits per hundred households. With the demand control: -8.0% per window per extra permit (-14.3% to -1.7%); without: -0.4% (-4.6% to +3.7%). Between the tenth and ninetieth percentile building rate: -17.7% over a window.

| Specification | Annual growth per permit per 100 households | Low | High | Over the window | Clusters |
|---|---:|---:|---:|---:|---:|
| with the demand control | -0.0160 | -0.0286 | -0.0034 | -8.0% | 85 |
| without the demand control | -0.0009 | -0.0092 | +0.0074 | -0.4% | 85 |

**Method.** Plan `a1d050c1b22c5986`; fixed effects on population weighted metro by window cells, alternating projections, two specifications; cluster robust by state, 85 clusters; non overlapping 5 year windows from 2001; permits shifted back one year. Window interior: degenerate. Simulator (truth -0.025): controlled mean bias +0.0026, uncontrolled +0.0058; under strong demand +0.0031 against +0.0078.

### What the housing economist would push back on

Permits respond to demand: a metro builds because prices are rising, which pushes the uncontrolled estimate toward zero or past it, and the recovery study measures that bias under every condition. The migration series is one demand shock, not all of them; income growth and investor demand are not in the regression. Permits are not completions, and a permit pulled in a downturn may never become a home. The notebook keeps the specification that put the demand shock in the wrong fixed effect as a dead end. And the window matters: the 5 year estimate is the only one of the three lengths tried whose interval excludes zero, which is the kind of result a reader should hold loosely until a second decade of permits is in.

## 5. The fair ranking

<!-- chart: ranking -->
**The ranking changes when you hold constant what people earn there: 17 of the 20 largest metros move beyond their intervals. Less affordable than their price says: Tampa-St. Petersburg-Clearwater from 106 to 90; Miami-Fort Lauderdale-West Palm Beach from 33 to 22; Los Angeles-Long Beach-Anaheim from 7 to 2. More affordable: St. Louis from 223 to 307; Minneapolis-St. Paul-Bloomington from 114 to 195; Washington-Arlington-Alexandria from 25 to 102.** 382 metropolitan areas ranked in 2024 by the anchored median value and by the payment share at the local median income, with rank intervals from 10,000 Monte Carlo draws over the census margins. Most expensive: San Jose-Sunnyvale-Santa Clara; San Francisco-Oakland-Fremont; Santa Cruz-Watsonville. Least affordable: Kahului-Wailuku; Los Angeles-Long Beach-Anaheim; Santa Cruz-Watsonville, led by Kahului-Wailuku, HI at 75.5% (69.7% to 81.7%). Rank correlation 0.94; mean rank change 29.1 places; largest 171 (Lexington Park, MD). Affordable share from 11% to 75%, median 53%.

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

**Method.** Plan `e23fc6df73f96272`; payment share at the local median income; affordable share by bracket interpolation; 10000 Monte Carlo draws over the income and anchor value margins, index held fixed. Simulator: adjusted ranking rank correlation with the truth 0.956 against 0.890 for the price ranking; bracket interpolation mean absolute error 0.4 pts.

### What the housing economist would push back on

The median income is not the buyer income: in a metro where buyers earn twice the median, the payment share of the median household overstates what the people who actually buy face, and chapter 6 measures that ratio from the loans. The index has no margin, so the interval understates what a thin market's index carries. Metros that lost their one year census coverage drop out of the ranking in that year rather than being carried.

## 6. Who still buys

<!-- chart: buyers -->
**The buyer is richer than in 2019 by +0.15 of the local median income (interval +0.12 to +0.19) and, against the claim, slightly younger: the under 35 share rose +1.2 pts (interval +0.1 pts to +2.3 pts) by 2025. The ratio moved most in Los Angeles-Long Beach-Anaheim +0.44; Miami-Fort Lauderdale-West Palm Beach +0.37; New York-Newark-Jersey City +0.30.** From 3,533,474 purchase originations in 2019 and 2,722,577 in 2025: borrower income over the metro median 1.23x to 1.39x (+0.15, +0.12 to +0.19); share earning over twice the median 20.9% to 26.7%; under thirty five share 38.3% to 39.4% (+1.2 pts, +0.1 pts to +2.3 pts); value to income 3.38x to 3.38x; median rate spread 0.19%.

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

**Method.** Plan `5714fb93ae481cb1`; weighted medians over five thousand dollar income bins per lender; shares as ratios of sums; bootstrap over lenders within year, 400 replicates; base year 2019; reported on 2025. Simulator: ratio shift mean bias -0.001; under thirty five shift -0.02 pts.

### What the housing economist would push back on

The HMDA income is the income the lender used, not the household's; a co-borrower or a self employed buyer is reported differently by different lenders, which is why the interval resamples lenders. The ratio compares buyers with the metro median household in the nearest census year, and the census has no 2020 release, so 2020 loans are compared with 2019 incomes. The purchase subset leaves out buyers who paid cash, who are the richest buyers of all.

## 7. The migration shock

<!-- chart: migration -->
**The metros that gained people were already lagging before the pandemic: the placebo on the years before it is -0.8% (interval -1.4% to -0.2%), so the headline of +1.5% price growth over the window per person gained per hundred residents beyond the pre pandemic pace is a lower bound on what the migration itself did.** Across 385 metros, price growth over 2019Q4 to 2021Q4 on the migration shock (per hundred residents, 2020 and 2021 less 2018 and 2019): +1.48% per person (+0.40% to +2.55%); placebo on 2016Q4 to 2018Q4: -0.78% (-1.35% to -0.20%); level alone with no control: +2.41%. Synthetic controls for Panama City-Panama City Beach; Amherst Town-Northampton; Fairbanks-College: peak gaps +9.4%, +1.5% and +0.5%; latest gaps -2.0%, +0.9% and -6.0%; permutation p values 0.829, 0.725 and 0.254.

| Window | Growth per person per 100 residents of shock | Low | High | p | Clusters |
|---|---:|---:|---:|---:|---:|
| 2019Q4 to 2021Q4 | +1.48% | +0.40% | +2.55% | 0.007 | 85 |
| 2016Q4 to 2018Q4 (placebo) | -0.78% | -1.35% | -0.20% | 0.009 | 85 |
| 2019Q4 to 2021Q4 (level alone, no pre pandemic control) | +2.41% | +1.87% | +2.95% | 0.000 | 85 |

**Method.** Plan `b2cbe5f6a4559c90`; cross section of metros on the migration shock with the pre pandemic migration as a control, one observation per metro, state clusters; synthetic control on the simplex with every donor searched; cluster robust by state, 85 clusters; permutation p values over 192 donors; window 2019Q4 to 2021Q4; placebo 2016Q4 to 2018Q4. Simulator: controlled estimate mean bias -0.02%, coverage 98%; level alone -0.30% with no reverse causality and -0.51% under strong; placebo flag rate 46% under strong reverse causality against 6% under none.

### What the housing economist would push back on

Migration follows affordability: people move to the metros they can afford, and a metro that was already cheap for its incomes was already on a different price path. On the simulator the regression on the migration level alone carries that bias and the pre pandemic control removes most of it, but the simulator's households move for one reason with one lag, and the placebo flags the planted reverse causality only part of the time; that is the limit this chapter admits in print. The population estimates count domestic migration from July to June, so the migration years and the price window overlap by two quarters and not four. Remote work moved demand without moving many people, and that part is not in the migration series.

## 8. The reader decision

<!-- chart: decision -->
**Buying beats renting only after 10.0 years in the typical metro (interval 1.0 years to beyond 30 years), and one point of rate moves the breakeven by +4.5 years. Longest to break even among the largest metros: Boston-Cambridge-Newton 21 years; Chicago-Naperville-Elgin 20 years; San Francisco-Oakland-Fremont 18 years.** At the 30% line, 10% down and 6.72%, the median household can afford the median home in 221 of 382 metros (58%); median affordable share 53%; down payment years 6.4 years in the typical metro, 16.8 years in Kahului-Wailuku, HI. Owner weighted median breakeven 10.0 years (1.0 years to beyond 30 years); 4% of paths never break even inside 30 years; one point of rate moves the breakeven by +4.5 years. Quickest: Miami-Fort Lauderdale-West Palm Beach (3 years); slowest: Boston-Cambridge-Newton (21 years).

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

**Method.** Plan `10988e362f89ee23`; closed form payment arithmetic; bracket interpolation; breakeven under the cost model on bootstrap paths; block bootstrap, blocks of 3 years, 400 paths per metro; paths from each metro's own history; reported in 2024 at the latest quarterly rate. Interior tests: line degenerate, down payment stable. Simulator, late arriving truth: mean error 4.42 years, interval coverage 70%.

### What the housing economist would push back on

A payment is not the whole cost of owning: the cost model adds taxes, insurance, maintenance and the costs of buying and selling, but not the roof that fails in year four, and it credits the renter with a return the renter has to earn. The paths are drawn from the metro's own past, which includes a decade nobody expects to repeat, and the interval is the spread of those paths, not a forecast. The down payment years assume a renter who saves a tenth of income with no help and no return, which is the simplest honest reading of the question. The 30% line is doing work: at 28%, the sensitivity line, the median household can afford the median home in 191 of the 382 metros rather than 221, and the majority reading goes with the line.

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
