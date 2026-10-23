# The warehouse

> Public data from the Federal Housing Finance Agency, the Census Bureau (American Community Survey, Building Permits Survey, Population Estimates), the Department of Housing and Urban Development and the Consumer Financial Protection Bureau (HMDA), with mortgage rates from Freddie Mac under its terms of use. Metros are real and appear as they do in the public record; no household, borrower or address appears. The findings are a portfolio analysis, not financial advice, not a market forecast and not a fair lending finding.

dbt over DuckDB, built by `doorstep warehouse`: 35 models, 164 tests, 0 failed in the last build. The external parquet files the data stage writes are the sources; the marts are copied to `results/marts` and the ones the site reads to `web/public/data/marts`.

## Layers

- **Staging** types one source each: `stg_fhfa`, `stg_acs`, `stg_fmr`, `stg_fmr_areas`, `stg_income_limits`, `stg_rates`, `stg_permits`, `stg_population`, `stg_loans`, `stg_delineations`, `stg_gazetteer`.
- **Intermediate** maps every source to the metro through its delineation vintage and aligns quarters to years: `int_county_vintage_map`, `int_metro_dim`, `int_fhfa_area` (divisions rolled up by owner households), `int_county_year` (permits and population by county, then by area), `int_acs_metro_year` (every census table wide, with margins), `int_loans_metro_year` and `int_purchase_loans`.
- **Marts** at the grains the story uses: `mart_metro_quarter` (66,164 rows: the index, the anchored value, the rate and the payment), `mart_metro_year` (25,245 rows: incomes, rents, tenure, burden counts, permits, population, migration, loan counts), `mart_national_year` (19), `mart_income_brackets` (157,488), `mart_rent_burden_by_income` (68,901), the borrower marts (`mart_borrowers_income`, `mart_borrowers_vti`, `mart_borrowers_spread`), and `mart_quarantine` (593 rows). The grain tables the metric layer reconciles against: `grain_acs` (2,361,590 rows), `grain_counties` (52,029) and `grain_loans` (55,529,246).

## Quarantine

27 named rules flag 34,243,070 rows across the sources and delete none; every flagged row keeps its flag through the warehouse, and the chapters filter on the flags they care about. The rules, by source: FHFA, a non positive index value, a missing quarter in a series and an implausible quarter to quarter jump; PMMS, a missing week and an implausible rate; ACS, a margin of error above the estimate, a negative margin, a jam value or a top coded median; HUD, a fair market rent out of bedroom order and income limits out of order; permits, negative units and a units total that does not add up; population, a non positive population and a vintage overlap for the same year; HMDA, an exempt or missing income, a missing rate, a term other than thirty years, a reverse mortgage or an open end or business purpose line, a property value below the loan amount and a metro code that does not resolve through the delineation of its year; the delineations, a county in two areas in one vintage and a malformed FIPS code. The report is `data.quarantine.by_rule` on RESULTS.md and `mart_quarantine` on the data page.

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

## Tests and exposures

Every model has `not_null` and `unique` tests on its grain, accepted value tests on the kinds and sources, relationship tests from every mart to `int_metro_dim`, and the crosswalk tests described in `docs/geography.md`; the exposures name the story, the explorer, the briefing, the workbook and the BI extracts as the consumers of the marts. The metric layer in `metrics/metrics.yml` defines each metric over the finest grain and over the mart, and `doorstep metrics` fails when the two disagree beyond floating point at any of 4 grains.
