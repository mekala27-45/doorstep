# Can anyone still afford a home

*A data story in 8 chapters, about 20 minutes to read. Every number below is rendered from the analysis manifest; none was typed.*

**The payment story happened in eighteen months while the price story took twenty years: the share of income the median home takes in 2024 sits +2.6 pts above 2006 (interval +2.4 pts to +2.8 pts).**

> Public data from the Federal Housing Finance Agency, the Census Bureau (American Community Survey, Building Permits Survey, Population Estimates), the Department of Housing and Urban Development and the Consumer Financial Protection Bureau (HMDA), with mortgage rates from Freddie Mac under its terms of use. Metros are real and appear as they do in the public record; no household, borrower or address appears. The findings are a portfolio analysis, not financial advice, not a market forecast and not a fair lending finding.

<!-- chapter: definition | 1 | definition -->
## Affordable is a decision
<!-- claim -->
**The payment story happened in eighteen months while the price story took twenty years: the share of income the median home takes in 2024 sits +2.6 pts above 2006 (interval +2.4 pts to +2.8 pts).**
<!-- step: price -->
Two numbers claim to measure the same thing. The first is the price of the median home divided by the median household income in the same metro. It is the number most stories lead with, and it moves slowly, because incomes and prices both compound. Across the 60 metropolitan areas in both the price index and the census release, weighted by owner households, the ratio stood at 3.6x in 2005 and 3.8x in 2024, a change of +3.6% over the whole span. The peak of the last cycle was 3.7x in 2006.
<!-- step: payment -->
The second number is what the same home costs to carry: the monthly payment on a thirty year mortgage with 10% down at the rate of each quarter, twelve of them divided by the median income. That is the number a household lives with. It stood at 24.1% in 2005, fell for a decade as rates fell, and in 2024 it is 26.8% (interval 26.6% to 27.0%), against a government line of 30%.
<!-- step: peak -->
Set the two side by side and the story of the last twenty years splits in half. The price story took two decades. The payment story happened between the first rate rise and the eighteen months that followed it. In 2024 the payment share sits +2.6 pts against the 2006 peak (interval +2.4 pts to +2.8 pts), and 47 of the 60 metros (78%) now sit above their own 2006 payment share. 23 metros (38%) sit above the 30% line for the median household. Affordable is a decision about which of these two numbers you let define the word.
<!-- method -->
Plan `ac7975b9fb0c601f`, registered before the estimate ran on real metros. the anchored index with the payment at the quarterly rate 2000 Monte Carlo draws over the census margins of error, index held fixed (2,000 draws). Split: no fitted parameter; the baseline years are 2005 to 2019 and the headline is the latest release. Family: one comparison, no correction. The level is the census median value in the anchor year 2019 moved by the regulator index; the anchor sensitivity table on the data page re-anchors every headline in 2015, 2017, 2019 and 2023 and the headline is stable across them. On the simulator with a planted self report bias, the anchored payment share recovers the truth with a mean bias of -0.02 pts and the self report correction a mean bias of -0.002.
<!-- pushback -->
Self reported values run high or low by metro, and the anchor carries that bias into every year. The anchor sensitivity table shows what moving the anchor year does to the headline, and the self report check prints the census value over the transaction values in the loan extract for the same year; neither removes the bias, they bound it. The payment is principal and interest only, so a reader who adds taxes and insurance will find every share here understated by the same amount in every year.
<!-- /chapter -->

<!-- chapter: rate_shock | 2 | rate_shock -->
## The rate shock and the lock in
<!-- claim -->
**The rate part of the payment overtook the price part in 2022Q3. The lock in coefficient (-0.02, interval -0.13 to +0.10) cannot be told from zero.**
<!-- step: price -->
Take the owner weighted median home as it was priced in 2019Q1 and ask what it costs to carry each quarter since. The payment was $1,208 a month at the start of the window. By 2024Q4 it was $2,191, a change of +$983. The chart splits that change exactly into two parts: what the price did, holding the rate at its starting level, and what the rate did, on the home as priced. The price part is the slow one. It built through the pandemic years and stands at +$424 in the latest quarter.
<!-- step: rate -->
The rate part is the fast one. It was close to nothing while the thirty year rate sat near its lows, then it took over the chart in a few quarters. In the latest quarter the rate part is +$559, 57% of the whole change; it peaked at +$599 in 2024Q3.
<!-- step: overtaking -->
The quarter the rate part overtook the price part was 2022Q3. That is the date of the payment story. The second half of this chapter asks what the shock did to the people who already owned. 1.7 million mortgages were originated in 2019 to 2021 at rates under 4.00%, and the lock in intensity is those loans per hundred owner households in each metro, from 10.4 at the tenth percentile to 11.7 at the ninetieth. Turnover, purchase originations per hundred owner households, fell from 1.63 in the base years to 1.17 after the shock. Regressed on the intensity with metro and year fixed effects, each point of lock in moved turnover by -0.019 (interval -0.132 to +0.095); the same regression on the two years before the shock, the placebo, gives +0.046 (interval -0.025 to +0.117). Between the tenth and ninetieth percentile metro that is -0.02 purchases per hundred owners.
<!-- method -->
Plan `dc55265cae0a0e21`. exact price and rate decomposition of the payment; turnover on lock in intensity with metro and year fixed effects on owner weighted cells; cluster robust by state, 9 clusters; event window 2019 to the latest quarter; base years 2018 and 2019; test years from 2023; headline and placebo reported separately. 240 metro by year cells over 60 metros. The threshold has its interior test on the shocks page: the headline under 3.0%, 3.5% and 4.0% is stable. On the simulator, where the lock in response is planted, the difference in differences recovers it with a mean bias of +0.0015 and 94% interval coverage.
<!-- pushback -->
Lock in is measured from originations, so a metro where owners refinanced twice at the bottom counts each refinance; the measure is an intensity, not a count of owners, and the notebook keeps the version that counted refinances twice as a dead end. Turnover also fell because inventory fell, and a metro with little inventory sees fewer purchases whatever its owners hold; the placebo bounds the trend, it does not remove the mechanism.
<!-- /chapter -->

<!-- chapter: burden | 3 | burden -->
## The rent burden is a distribution, not a median
<!-- claim -->
**The median renter is burdened in most metros (100% of them) in 2024; the problem is the whole distribution, with 32.5% of renters paying half or more. The national series moved and stayed moved in 2009, 2013, 2018, 2022.**
<!-- step: bands -->
The census asks every renter what share of income the rent takes and publishes the answer in bands. The two lines that matter are the ones the government draws: cost burdened at 30% of income and severely burdened at 50%. Across the 60 metros in 2024, 57.8% of renter households with a computed share pay 30% or more (interval 54.0% to 61.8%). In 0 of those metros (0%) the median renter sits under the line. A story that reports the median rent against the median renter income can report either of those facts and miss the other.
<!-- step: severe -->
The severe band is the one a median hides entirely. 32.5% of renter households pay half or more of their income in rent (interval 29.3% to 36.3%), against the 20% line this chapter stated before it looked. Nationally the severe share went from 28.1% in 2005 to 32.5% in 2024, a change of +4.4 pts. By household income the picture is a cliff: among renters in the lowest income group 75% are severely burdened in 2024; in the highest group it is 0%. Owners with a mortgage sit beside them for scale: 28.0% pay 30% or more of income in owner costs.
<!-- step: changepoints -->
Did the national severe series drift, or did it move and stay moved? A changepoint search with a penalty fixed before the data finds 4 breaks, in 2009, 2013, 2018, 2022. The years are on the chart; the reader can decide what each one was. What the search rules out is a smooth line.
<!-- method -->
Plan `a2850a134d98e2a1`. burdened and severely burdened renters over renters with a computed share; PELT with a BIC penalty on the national series; block bootstrap over metros, 200 replicates; census ratio margins per metro; no fitted parameter; the penalty and the stated line are fixed before the data; the headline is the latest release; one comparison against the stated line. The severe line has its interior test on the data page: the headline under 15%, 20% and 25% is stable. On the simulator the severe share recovers the planted distribution with a mean bias of 0.00 pts, and the changepoint search lands within a year of the planted step in 100% of worlds.
<!-- pushback -->
Gross rent as a share of income is computed only for renters who reported both, and the census excludes those it could not compute; a metro where many students or retirees rent shows a high severe share that is income, not rent. The bands are left closed at thirty and fifty percent because the census publishes them that way, and a household at 29.9 percent is counted as unburdened by a line it did not choose.
<!-- /chapter -->

<!-- chapter: supply | 4 | supply -->
## Where builders kept pace, prices rose less
<!-- claim -->
**Where builders kept pace, prices rose less: 10.7% less price growth over 5 years per extra permit per hundred households (interval -13.8% to -7.6%); without the demand control the estimate is -8.3%.**
<!-- step: cells -->
Every metro is cut into 5 year windows from 2006 to 2020, 3 windows and 180 cells over 60 metros. For each cell the chart plots the building rate, permits per hundred households averaged over the window and shifted back one year so that permits lead prices, against the annual price growth of the window. The building rate runs from 0.60 at the tenth percentile cell to 1.89 at the ninetieth, around a mean of 1.23. The spec asked for permits per new household; that ratio has no value in a metro that lost households, which 78% of cells avoid, so it is published as a descriptive beside the rate (median 1.29) and the decision is logged.
<!-- step: controlled -->
With metro and window fixed effects, each extra permit per hundred households is associated with -10.7% price growth over the window (interval -13.8% to -7.6%), with domestic migration per hundred residents over the window and the two years before it in the regression as the observed demand shock. Between the tenth and the ninetieth percentile building rate that is -13.8% over a window.
<!-- step: both -->
Take the demand control out and the estimate is -8.3% (interval -12.1% to -4.5%). The two are published side by side because the gap between them is the size of the objection: builders build where people are arriving, and a regression that cannot see the arrivals credits the building with what the demand did. The simulator, where the elasticity is planted at -0.025, puts the controlled estimate's mean bias at +0.0026 and the uncontrolled at +0.0058; under strong demand the uncontrolled bias is +0.0078 against +0.0031 with the control. Both estimates are pulled toward zero when builders also answer the price growth they are regressed on, and the recovery table on the data page quantifies that by condition, which is why the headline is read as a lower bound in size.
<!-- method -->
Plan `a1d050c1b22c5986`. fixed effects on population weighted metro by window cells, alternating projections, two specifications; cluster robust by state, 9 clusters; non overlapping 5 year windows from 2006; permits shifted back one year; two specifications reported side by side. The window length has its interior test: the headline under windows of 3, 5 and 7 years is stable.
<!-- pushback -->
Permits respond to demand: a metro builds because prices are rising, which pushes the uncontrolled estimate toward zero or past it, and the recovery study measures that bias under every condition. The migration series is one demand shock, not all of them; income growth and investor demand are not in the regression. Permits are not completions, and a permit pulled in a downturn may never become a home. The notebook keeps the specification that put the demand shock in the wrong fixed effect as a dead end.
<!-- /chapter -->

<!-- chapter: ranking | 5 | ranking -->
## The least affordable metros are not the most expensive ones
<!-- claim -->
**The ranking changes when you hold constant what people earn there: 10 of the 20 largest metros move beyond their intervals. Less affordable than their price says: Simulated metro 38 from 37 to 18; Simulated metro 53 from 35 to 23; Simulated metro 12 from 31 to 20. More affordable: Simulated metro 46 from 4 to 15; Simulated metro 15 from 39 to 49; Simulated metro 23 from 33 to 37.**
<!-- step: raw -->
Rank the 60 metropolitan areas by the price of the median home in 2024 and you get the ranking every list publishes. The three most expensive are Simulated metro 1; Simulated metro 30; Simulated metro 43; the three cheapest are Simulated metro 54; Simulated metro 3; Simulated metro 35. 0 micropolitan areas are in the warehouse and the explorer but not in this ranking, because the one year census release covers only the largest of them and a ranking with holes in it is not a ranking.
<!-- step: adjusted -->
Now rank the same metros by the payment on that home as a share of what the median household there earns, and carry the census margins of error through 2,000 Monte Carlo draws so that every rank has an interval. The three least affordable are Simulated metro 1; Simulated metro 5; Simulated metro 43; the three most affordable are Simulated metro 31; Simulated metro 3; Simulated metro 35. The least affordable metro, Simulated metro 1, asks 49.9% of the median income (interval 46.8% to 53.5%); the most affordable, Simulated metro 35, asks 16.0%. The rank correlation between the two rankings is 0.90, the mean rank change is 5.4 places and the largest is 29, for Simulated metro 59, from 18 by price to 47 by payment share. Among the 20 largest metros, 10 move beyond their rank interval. A third measure, the share of local households whose income clears the payment on the median home at the 30% line, runs from 16% to 80% across the metros with a median of 55%.
<!-- method -->
Plan `e23fc6df73f96272`. payment share at the local median income; affordable share by bracket interpolation; 2000 Monte Carlo draws over the income and anchor value margins, index held fixed; descriptive, latest census year; one ranking; movers judged by their rank interval. On the simulator, where the true affordability ranking is known and the expensive metros were given the high incomes on purpose, the adjusted ranking's rank correlation with the truth is 0.956 against 0.890 for the price ranking, and the bracket interpolation's mean absolute error against the exact affordable share is 0.4 pts.
<!-- pushback -->
The median income is not the buyer income: in a metro where buyers earn twice the median, the payment share of the median household overstates what the people who actually buy face, and chapter 6 measures that ratio from the loans. The index has no margin, so the interval understates what a thin market's index carries. Metros that lost their one year census coverage drop out of the ranking in that year rather than being carried.
<!-- /chapter -->

<!-- chapter: buyers | 6 | buyers -->
## Who still buys
<!-- claim -->
**The buyer is richer than in 2019 by +0.09 of the local median income (interval +0.08 to +0.10), but not measurably older: the under 35 share moved -0.2 pts with an interval that includes zero. The ratio moved most in Simulated metro 12 +0.20; Simulated metro 33 +0.17; Simulated metro 56 +0.15.**
<!-- step: ratio -->
The loans say who got a mortgage. From the purchase subset of the mortgage disclosure extract, 251,037 originations across 40 lenders in 2019 and 189,323 across 40 in 2024, the median purchase borrower earned 1.35x the median household income of the metro in 2019 and 1.43x in 2024, a move of +0.09 (interval +0.08 to +0.10, resampling lenders). The share of buyers earning more than twice the local median went from 18.8% to 22.5%, +3.7 pts. The ratio moved most in Simulated metro 12, +0.20, and 18 of the 20 largest metros moved beyond their intervals.
<!-- step: age -->
Age is the other half of the question. Buyers under thirty five were 34.1% of purchase borrowers with a reported age in 2019 and 33.9% in 2024, a move of -0.2 pts (interval -0.5 pts to +0.1 pts). The median property value to borrower income went from 2.62x to 2.62x, and the rate spread over the benchmark sat at 0.31% for the median loan, from -0.19% to 0.81% across the deciles. Denials are not in this chapter: fair lending is a different build with a different standard of evidence, and the race and ethnicity fields were not loaded.
<!-- method -->
Plan `fa89aa88427acdac`. weighted medians over five thousand dollar income bins per lender; shares as ratios of sums; bootstrap over lenders within year, 200 replicates; base year 2019; reported on 2024; two differences on their own intervals. Incomes arrive in thousands and values at the midpoints of their reporting bins; the rounding rules are part of the extract contract on the buyers page. On the simulator, where the shift in the buyer pool is planted, the ratio shift recovers with a mean bias of -0.001 and the under thirty five shift with -0.02 pts.
<!-- pushback -->
The HMDA income is the income the lender used, not the household's; a co-borrower or a self employed buyer is reported differently by different lenders, which is why the interval resamples lenders. The ratio compares buyers with the metro median household in the nearest census year, and the census has no 2020 release, so 2020 loans are compared with 2019 incomes. The purchase subset leaves out buyers who paid cash, who are the richest buyers of all.
<!-- /chapter -->

<!-- chapter: migration | 7 | migration -->
## The migration shock
<!-- claim -->
**Demand moved and prices followed: +1.5% price growth over the window per person gained per hundred residents beyond the pre pandemic pace (interval +1.2% to +1.9%), with a placebo of 0.0% on the years before the pandemic whose interval includes zero.**
<!-- step: scatter -->
In 2020 and 2021 people moved. The shock this chapter measures is domestic migration per hundred residents over those two years less the same measure over 2018 and 2019, so that a metro which gained people every year is not credited with a pandemic it did not have. Across 60 metros the shock runs from -2.86 at the tenth percentile to +1.85 at the ninetieth. Against it the chart plots price growth from 2019Q4 to 2021Q4, which averaged 11.9%. The slope is +1.54% per person gained per hundred residents (interval +1.23% to +1.86%), which between the tenth and the ninetieth percentile metro is +7.3% of price growth. The regression a reader would run first, growth on the pandemic migration level alone with no control, gives +0.96% (interval +0.71% to +1.21%); it is on the shocks page because the simulator shows what the control removes.
<!-- step: placebo -->
The objection is that the metros that gained people were already on a different path. The placebo asks the same question of the years before the pandemic: growth from 2016Q4 to 2018Q4 on the same shock, with the migration of those years as its control. It is -0.04% (interval -0.48% to +0.41%). The message rule reads the two intervals together and has a branch for every outcome, including the one where the placebo moves.
<!-- step: synthetic -->
For the 3 metros with the largest shocks, Simulated metro 37; Simulated metro 26; Simulated metro 40, a synthetic control is built from the metros whose shock was small, with every donor searched and then treated in turn as a placebo. Simulated metro 37 ran +3.8% above its synthetic twin at the peak and -2.6% in the latest quarter, with a permutation p value of 0.774 over 30 donors; Simulated metro 26 ran +7.9% at the peak and +7.9% now (0.355); Simulated metro 40 ran +2.1% and -3.3% (0.839). The gap after the shock window is the reversal, or its absence, and the chart shows it rather than naming it.
<!-- method -->
Plan `b2cbe5f6a4559c90`. cross section of metros on the migration shock with the pre pandemic migration as a control, one observation per metro, state clusters; synthetic control on the simplex with every donor searched; cluster robust by state, 9 clusters; permutation p values over 30 donors; window 2019Q4 to 2021Q4; placebo 2016Q4 to 2018Q4; headline and placebo reported separately. On the simulator the controlled estimate recovers the planted response with a mean bias of -0.02% and 98% coverage; the regression on the level alone carries a bias of -0.30% with no reverse causality and -0.51% under strong reverse causality; and the placebo flags the strong reverse causality condition in 46% of worlds against 6% when there is none. That last pair is the power of the test, and it is the limit this chapter admits in print.
<!-- pushback -->
Migration follows affordability: people move to the metros they can afford, and a metro that was already cheap for its incomes was already on a different price path. On the simulator the regression on the migration level alone carries that bias and the pre pandemic control removes most of it, but the simulator's households move for one reason with one lag, and the placebo flags the planted reverse causality only part of the time; that is the limit this chapter admits in print. The population estimates count domestic migration from July to June, so the migration years and the price window overlap by two quarters and not four. Remote work moved demand without moving many people, and that part is not in the migration series.
<!-- /chapter -->

<!-- chapter: decision | 8 | decision -->
## The reader decision
<!-- claim -->
**Buying beats renting only after 15.0 years in the typical metro (interval 2.0 years to beyond 30 years), and one point of rate moves the breakeven by +5.5 years. Longest to break even among the largest metros: Simulated metro 29 beyond 30 years; Simulated metro 14 beyond 30 years; Simulated metro 47 beyond 30 years.**
<!-- step: curve -->
Everything above is about places. This chapter is about a household. At the 30% line, 10% down and the latest quarterly rate of 6.88%, the median household can afford the median home in 37 of 60 metros (62%); across metros the affordable price sits a median of +$27,096 from the median home, and a median of 55% of local households clear the payment on it. A renter at the renter median income saving 10% of income needs 6.1 years to reach the down payment in the typical metro and 11.4 years in Simulated metro 1. The chart draws the rent or buy question for Simulated metro 29: the cumulative cost of owning net of the equity built, less the cumulative cost of renting with the down payment invested instead, year by year to a 30 year horizon. Where the curve crosses zero is the breakeven; here it is beyond 30 years.
<!-- step: breakeven -->
The paths behind the curve are not a forecast. Appreciation and rent growth are drawn in blocks of three years from the metro's own history, 200 paths per metro, and the band is the spread of those paths. Across the metros with enough history, 60 of them, the owner weighted median breakeven is 15.0 years (interval 2.0 years to beyond 30 years), and in 36% of paths owning does not catch up inside the horizon at all. One point of rate moves the median breakeven by +5.5 years. The quickest breakevens among the largest metros are Simulated metro 15 (3 years), Simulated metro 48 (6 years) and Simulated metro 46 (6 years); the slowest are Simulated metro 29 (beyond 30 years), Simulated metro 14 (beyond 30 years) and Simulated metro 47 (beyond 30 years). The planner page runs the same arithmetic for any metro, income, rate, down payment and horizon, through the live API, and logs the check so that the next quarter of prices and rates can grade it.
<!-- method -->
Plan `10988e362f89ee23`. closed form payment arithmetic; bracket interpolation; breakeven under the cost model on bootstrap paths; block bootstrap, blocks of 3 years, 200 paths per metro; paths from each metro's own history; reported in 2024 at the latest quarterly rate; one headline. Three operating points have their interior tests on the data page: the line (25%, 28%, 30% and 35%) is degenerate, the down payment (5%, 10% and 20%) is stable, and the saving rate (5%, 10% and 15%) is printed beside them. On the simulator the breakeven is graded as late arriving truth: the estimate made from the history to a stated year against the breakeven the realised path produced, with a mean error of 4.42 years and 70% interval coverage; the simulated decade after the estimate held a boom the history did not, which is the caveat on every breakeven here.
<!-- pushback -->
A payment is not the whole cost of owning: the cost model adds taxes, insurance, maintenance and the costs of buying and selling, but not the roof that fails in year four, and it credits the renter with a return the renter has to earn. The paths are drawn from the metro's own past, which includes a decade nobody expects to repeat, and the interval is the spread of those paths, not a forecast. The down payment years assume a renter who saves a tenth of income with no help and no return, which is the simplest honest reading of the question.
<!-- /chapter -->

## Corrections

No published number has been corrected since the first release. Corrections will appear here, dated, with what the earlier version said, what it says now, and why.

## How this was built

Prices from the regulator index for every metropolitan area it covers from 1975 to 2026Q2, incomes, rents and tenure from every one year census release from 2005 to 2024 with the 2020 release carried as a gap, weekly mortgage rates, permits, population with its components, and 0 mortgage originations from 2018 to 2024 went through 26 named quarantine rules into a dbt warehouse whose metric layer defines each number once and reconciles it at 4 grains. Each chapter's plan was hashed before its estimate touched a real metro, and each estimator was first run on a simulated country of 60 metros where the answer is known, over 24 conditions and 20 seeds each. The story, the briefing, the site and the workbook all render from one manifest, so a number here is the number everywhere.

The method appendix, the definitions, the warehouse and the recovery study are on the [data page](data/), the calculator is on the [planner page](planner/), and every chart's SQL is one click from the chart.
