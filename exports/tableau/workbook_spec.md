# Tableau companion specification

Extracts: `metro_year.csv`, `metro_quarter.csv`, `national_year.csv`, `ranking.csv`, `burden_bands.csv`, `supply_cells.csv`

- **Payment share over time** (metro_year): line by cbsa_title, year on columns, payment_share on rows; reference: constant line at 0.30, the HUD standard.
- **Price against income** (metro_year): scatter of median_income (columns) against value_anchored (rows) for the latest year, size by households, color by payment_share; reference: diagonal at price to income 4.
- **Rank slope** (ranking): slope chart from raw_rank to adjusted_rank for the twenty largest metros, color by moves; reference: rank 1 at the top.
- **Rent burden bars** (burden_bands): stacked bars by year of under_30, from_30_to_50 and over_50; reference: lines at 30 and 50 percent.
- **Permits against price growth** (supply_cells): scatter of permits_rate (columns) against annual_growth (rows), trend line with confidence band; reference: the controlled slope from the manifest.

Public data from the Federal Housing Finance Agency, the Census Bureau (American Community Survey, Building Permits Survey, Population Estimates), the Department of Housing and Urban Development and the Consumer Financial Protection Bureau (HMDA), with mortgage rates from Freddie Mac under its terms of use. Metros are real and appear as they do in the public record; no household, borrower or address appears. The findings are a portfolio analysis, not financial advice, not a market forecast and not a fair lending finding.

Mortgage rates: Freddie Mac Primary Mortgage Market Survey, used under its terms of use.
