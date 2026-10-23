# Decisions

Dated, in the order they were made. A heading that starts with `Reversal` undid an earlier decision; one that starts with `Correction` changed a published number and renders into the corrections section of the story and the briefing.

## 2026-10-22: The index is the regulator's, the level is the census's

The dollar level of every price is the ACS median value of owner occupied units in 2019 moved by the FHFA index. 2019 is the last full response year before the pandemic. The alternative, a vendor dollar series, is one private estimate of both the movement and the level under terms that do not allow redistribution; the anchor is a stated decision with a sensitivity table (2015, 2017, 2019 and 2023) beside every headline. The purchase only seasonally adjusted index is the primary series; where FHFA publishes only the all transactions index for an area, or for the years before the purchase only series starts, that series is used and the source is labeled on every row of `mart_metro_quarter`.

## 2026-10-22: Metropolitan divisions roll up to the area by owner households

FHFA publishes divisions for the largest areas. The area is what the census, the permits and the population files describe, so the divisions are rolled up to the area through the delineation file of the quarter, weighted by owner households, and the definitions document says so. A division level view is a stretch item.

## 2026-10-22: The HMDA source is the CFPB snapshot, filtered as the file is read

The data browser refused the nationwide pull with the filter in the URL, so the fetch takes the annual snapshot zip per year and applies the filter (action taken 1; loan purposes 1, 31 and 32; occupancy type 1) as the file streams, writing gzip parts and a summary with the row counts before and after. The occupancy filter is also applied at ingest as a quarantine rule, so a part that carried a second home by mistake is flagged rather than trusted. Nothing inside the window is sampled, and the provenance file records the filter and every count.

## 2026-10-22: The population estimates count a year from July to June

The components of change are published for estimate years that run from July to June. The migration measures use the estimate year as published and the price windows use calendar quarters, so a migration year and the price window that follows it overlap by two quarters rather than four. The alternative, interpolating migration to calendar years, would invent a number the Census Bureau did not publish.

## 2026-10-22: Table B25074 changes its layout in 2015

Gross rent as a percentage of income by household income carried seven cells per income group (five rent bands) through 2014 and nine from 2015. The fetch requests fifty cells for the earlier years and sixty four from 2015, the mart handles both layouts through a cell offset, and the simulator's export mirrors the layout by year so the warehouse tests run on both.

## 2026-10-22: The severe share line is twenty percent

Chapter 3's message rule needs a line for the severely burdened share, stated before the data. Twenty percent of renters paying half or more of their income is the line, with fifteen and twenty five as the interior test. The spec left the value open; the earlier affordability literature puts the national severe share near a quarter, so twenty is a line the data could have sat on either side of.

## 2026-10-22: Reversal, the supply regressor is permits per hundred households

The spec asked for permits per new household. That ratio is undefined where a metro lost households, which about one metro window in five does on the real files, and it explodes where households barely moved. The regressor is the building rate, permits per hundred households averaged over the window and shifted back one year; permits per new household is published as a descriptive beside it with the share of cells where it is defined. The plan hash of chapter 4 changed and was re-registered before the real run.

## 2026-10-22: The simulator's builders answer last year's arrivals, weakly the price growth

The first version of the simulator had permits respond only to last year's price growth, with a gain that doubled the building rate on a four point growth surprise. Under price noise the supply estimator came back attenuated by half, and the demand control could not remove it, because the bias was a feedback artifact: builders answering the very growth they were regressed on inside the window. The second version has permits follow last year's domestic migration (the demand shock the chapter controls for, with a one year lag because a permit follows the inflow it answers) and the price growth only weakly (ten percent per four points at unit elasticity). The recovery study now shows the bias the chapter was designed to show, the demand confound the control removes, and a smaller residual attenuation that the chapter reports as the reason its headline is a lower bound in size.

## 2026-10-22: Migration in the simulator persists, and answers the gap two years back

Migration swings last several years (an autoregressive component with persistence 0.7), which is what makes the demand shock a confounder for the supply chapter. Under reverse causality households answer the affordability gap of two years back rather than last year's, because a move takes that long and because the lag is what gives the pre trend placebo its power: the metros people are leaving were already growing more slowly.

## 2026-10-23: Reversal, the migration regression weights metros equally

The first version weighted the cross section by population. On the simulator the placebo then flagged a pre trend in about one world in four under the null with high noise, because a third of the weight sat on four metros and the cluster robust variance understated the spread of the placebo across worlds. With one observation per metro the false flag rate is about one in fourteen and the headline's coverage is unchanged. The pre pandemic level control was also moved from 2017 and 2018 to 2018 and 2019, the two years right before the shock, and the placebo controls for the migration of its own window rather than the pre pandemic level.

## 2026-10-23: Cluster robust intervals use the t distribution on clusters minus one

With fifteen simulated states and fifty real ones, the normal approximation on a cluster robust t statistic runs narrow. Intervals and p values use the t distribution with one fewer degree of freedom than there are clusters, the small cluster convention, and the recovery study reports the coverage that results.

## 2026-10-23: The known truth tests run without price noise

The known truth tests are the three conditions the spec names (no noise, no confounding, every estimator recovers the planted value) and they run on a condition with the noise knob at zero, which exists for the tests only; the recovery study, not the tests, grades the estimators under noise. The supply test tolerance is a tenth of the planted elasticity, the residual being the annual index that is the mean of its quarters.

## 2026-10-23: The palette validator moved three values

The validator ported from the previous builds rejected three of the stated values and each was moved by the smallest change that passes: the light sequential ramp's first two steps lightened to `#A6D1BB` and `#7CBC9D` so the ramp stays monotonic in lightness against the surface, and the dark categorical slot one darkened to `#2FC79A` so the first three slots pass the all pairs check on the dark card. Every other value is as stated, and the validator runs in CI against the committed file including the dark card run.

## 2026-10-23: The HMDA year is read a part at a time

Reading a year of the extract into one frame with its flags took six gigabytes on a seven gigabyte machine and the first full run was killed. Each gzip part is typed, flagged and written on its own; the year's parquet is then written by DuckDB streaming the parts under its memory limit, and the quarantine report is the sum over parts. The year's parquet is cached by a digest of the parts and the contract, so a rerun that changes nothing reads nothing.

## 2026-10-23: The rent burden table changed layout with the 2014 release, not 2015

The fetch script asked for fifty cells of table B25074 through 2014 on the strength of a comment. The first real warehouse failed its burden test with negative renter counts in 2014 alone, and the cells showed the sixty four cell layout already in that release: the fifty cells fetched were the first fifty of nine per group. The script and the mart now switch with the 2013 release, the 2014 table was fetched again, and the warehouse test that caught it stays as it is.

## 2026-10-23: Puerto Rico's areas are outside the price test and every anchored chapter

Four Puerto Rico metropolitan areas are in the delineation with census rows and loans, and FHFA publishes no index for them. The warehouse test that asks for a year of prices in every metropolitan area with more than two hundred thousand households failed on San Juan alone. The test leaves Puerto Rico out by name rather than lowering the threshold, and the geography page says so.

## 2026-10-23: Counties on the latest delineation, census areas through an alias table

The first warehouse mapped every county through the delineation in force in the data year, as the spec reads, and the first real build failed the metric reconcile: the county roll up carried a hundred area codes the latest delineation no longer has, and Connecticut's metros had no population at all for 2020 to 2022, because the planning regions that replaced its counties are not in the 2020 vintage. The county sources (permits, population, the loans, the HUD files) are now placed on the latest delineation for every year, so a metro is the same counties throughout, and a retired county code maps through the last vintage that carried it. The census, which publishes by area, resolves its codes through an alias table derived from the delineation files: an earlier code goes to the latest area that holds more than half of its counties. The reconciliation the spec asks for is run on population rather than owner households, because the one year census tables carry no county level owner counts: the roll up reproduces the Bureau's own published metro totals of the latest vintage within a tenth of a percent, and that test is in the warehouse.

## 2026-10-23: Two more rules from the first real build, and a fetch that was only partly carried over

The permit files for 2014 and 2015 list five counties twice, under two spellings of one name with the same figures (Anchorage, Juneau, Sitka, Yakutat, St. Marys); the warehouse's uniqueness test caught it, and a quarantine rule now flags the second row and the staging model carries the county once. The permit window also refuses a missing year, because the first real build ran on three of the twenty seven county files the fetch had already put on the laptop, and nothing stopped it: the warehouse built, the chapters would have run, and the supply chapter would have had no permits in any window. The 2025 loan file, published this year, was carried over at the same time.
