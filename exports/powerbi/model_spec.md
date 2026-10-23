# Power BI model specification

## Tables

- `metro_year` from tableau/metro_year.csv; key cbsa_code, year; every column of mart_metro_year.
- `metro_quarter` from tableau/metro_quarter.csv; key cbsa_code, period; index, anchored value, rate, payment, payment share.
- `ranking` from tableau/ranking.csv; key cbsa_code; the raw and adjusted ranks of 20 metros with intervals.
- `metros` from tableau/metro_year.csv (distinct cbsa_code, cbsa_title, kind, states); key cbsa_code; the dimension.
- `years` from generated; key year; a date table from 2000.

## Relationships

- metro_year[cbsa_code] to metros[cbsa_code] (many to one).
- metro_quarter[cbsa_code] to metros[cbsa_code] (many to one).
- ranking[cbsa_code] to metros[cbsa_code] (one to one).
- metro_year[year] to years[year] (many to one).

## Measures (DAX)

- **Payment share** (pct): `DIVIDE(12 * SUM(metro_year[payment]), SUM(metro_year[median_income]))`
- **Price to income** (ratio): `DIVIDE(SUM(metro_year[value_anchored]), SUM(metro_year[median_income]))`
- **Affordable share** (pct): `AVERAGE(ranking[affordable_share])`
- **Cost burdened share** (pct): `DIVIDE(SUM(metro_year[renters_burdened]), SUM(metro_year[renters_with_share]))`
- **Severely burdened share** (pct): `DIVIDE(SUM(metro_year[renters_severe]), SUM(metro_year[renters_with_share]))`
- **Permits per 100 households** (ratio): `DIVIDE(100 * SUM(metro_year[permits]), SUM(metro_year[households]))`
- **Lock in share** (ratio): `DIVIDE(100 * CALCULATE(SUM(metro_year[low_rate_originations]), metro_year[year] IN {2019, 2020, 2021}), CALCULATE(SUM(metro_year[owner_households]), metro_year[year] = 2021))`
- **Turnover per 100 owners** (ratio): `DIVIDE(100 * SUM(metro_year[purchase_loans]), SUM(metro_year[owner_households]))`
- **Borrower income ratio** (ratio): `DIVIDE(SUM(metro_year[purchase_median_income]), SUM(metro_year[median_income]))`
- **Domestic migration per 100** (ratio): `DIVIDE(100 * SUM(metro_year[domestic_migration]), SUM(metro_year[population]))`

Build the model on Windows from these tables and measures and commit the .pbip; the companion reads the same marts the site reads.

Public data from the Federal Housing Finance Agency, the Census Bureau (American Community Survey, Building Permits Survey, Population Estimates), the Department of Housing and Urban Development and the Consumer Financial Protection Bureau (HMDA), with mortgage rates from Freddie Mac under its terms of use. Metros are real and appear as they do in the public record; no household, borrower or address appears. The findings are a portfolio analysis, not financial advice, not a market forecast and not a fair lending finding.

Mortgage rates: Freddie Mac Primary Mortgage Market Survey, used under its terms of use.
