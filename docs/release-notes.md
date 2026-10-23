# doorstep v0.1.0

Can anyone still afford a home: a data story in 8 chapters, built on every metropolitan area present in both the regulator price index and the census one year release (393 of them) from 2000 to 2026Q2, with the warehouse, the simulator that proves each estimator before it touches a real metro, an affordability calculator on a small API, and the exports a BI team would open.

> Public data from the Federal Housing Finance Agency, the Census Bureau (American Community Survey, Building Permits Survey, Population Estimates), the Department of Housing and Urban Development and the Consumer Financial Protection Bureau (HMDA), with mortgage rates from Freddie Mac under its terms of use. Metros are real and appear as they do in the public record; no household, borrower or address appears. The findings are a portfolio analysis, not financial advice, not a market forecast and not a fair lending finding.

## The findings

- **Affordable is a decision.** The payment share of 2024 does not exceed 2023; the payment story is not yet the largest the window has seen. It sits +1.1 pts above 2006 (interval +1.0 pts to +1.3 pts), so the 2006 peak is passed, and the window's own peak is 2023.
- **The rate shock and the lock in.** The rate part of the payment overtook the price part in 2023Q3. The rate shock froze turnover where owners had the most to lose: 0.06 fewer purchases per 100 owner households per point of lock in (interval -0.08 to -0.03), and the placebo on the years before the shock sits at 0.00 with an interval that includes zero.
- **The rent burden is a distribution problem.** The median renter is burdened in 51% of metros in 2024, so the median hides nothing; the problem is the whole distribution, with 26.5% of renters paying half or more (interval 25.7% to 27.2%). The national series moved and stayed moved in 2009, 2015, 2021.
- **Where builders kept pace, prices rose less.** Where builders kept pace, prices rose less: 8.0% less price growth over 5 years per extra permit per hundred households (interval -14.3% to -1.7%); without the demand control the estimate is -0.4%.
- **The fair ranking.** The ranking changes when you hold constant what people earn there: 17 of the 20 largest metros move beyond their intervals. Less affordable than their price says: Tampa-St. Petersburg-Clearwater from 106 to 90; Miami-Fort Lauderdale-West Palm Beach from 33 to 22; Los Angeles-Long Beach-Anaheim from 7 to 2. More affordable: St. Louis from 223 to 307; Minneapolis-St. Paul-Bloomington from 114 to 195; Washington-Arlington-Alexandria from 25 to 102.
- **Who still buys.** The buyer is richer than in 2019 by +0.15 of the local median income (interval +0.12 to +0.19) and, against the claim, slightly younger: the under 35 share rose +1.2 pts (interval +0.1 pts to +2.3 pts) by 2025. The ratio moved most in Los Angeles-Long Beach-Anaheim +0.44; Miami-Fort Lauderdale-West Palm Beach +0.37; New York-Newark-Jersey City +0.30.
- **The migration shock.** The metros that gained people were already lagging before the pandemic: the placebo on the years before it is -0.8% (interval -1.4% to -0.2%), so the headline of +1.5% price growth over the window per person gained per hundred residents beyond the pre pandemic pace is a lower bound on what the migration itself did.
- **The reader decision.** Buying beats renting only after 10.0 years in the typical metro (interval 1.0 years to beyond 30 years), and one point of rate moves the breakeven by +4.5 years. Longest to break even among the largest metros: Boston-Cambridge-Newton 21 years; Chicago-Naperville-Elgin 20 years; San Francisco-Oakland-Fremont 18 years.

## Where it runs

- The story and its pages: not yet published
- The calculator's API: not yet deployed- The briefing: `report/briefing.md` and `report/briefing.html`

## In this release

- 85,272 index rows, 2,415,786 census estimates over 19 releases, 2,900 weekly rates, 81,768 permit rows, 81,714 population rows and 137,678,531 mortgage records, nothing sampled; 27 quarantine rules.
- 35 dbt models and 164 tests; 21 metrics reconciled at 4 grains over 1,764 cells with 0 disagreements.
- The recovery study: 480 simulated worlds over 24 conditions and 20 seeds, 17 estimators, 8,160 grades.
- Eight registered plans, each hash in `results/chapters/plans.json` and printed in every method note.
- The workbook with live formulas, the Tableau and Power BI specifications and the CSV bundle in `exports/`.

## The definition of done

13 of 18 lines done; not done: 7, 13, 14, 15, 18. The README prints every line with its evidence.
