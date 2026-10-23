# Provenance

> Public data from the Federal Housing Finance Agency, the Census Bureau (American Community Survey, Building Permits Survey, Population Estimates), the Department of Housing and Urban Development and the Consumer Financial Protection Bureau (HMDA), with mortgage rates from Freddie Mac under its terms of use. Metros are real and appear as they do in the public record; no household, borrower or address appears. The findings are a portfolio analysis, not financial advice, not a market forecast and not a fair lending finding.

Every file the build reads is listed in `data/ingest_ledger.csv` with its byte count and SHA-256 checksum (575 files, 2,573,273,827 bytes in the last run), written by the data stage; the fetch status files under `data/external` record every URL asked for, its row count and the latest period each source had published when it was fetched.

| Source | Files | Window in the build | Latest period | License and terms |
|---|---|---|---|---|
| Federal Housing Finance Agency, House Price Index master file (`hpi_master.csv`) | `data/external/fhfa` | 1975 to 2026Q2, 85,272 rows | 2026Q2 | U.S. government work, public domain |
| Census Bureau, American Community Survey one year release, by API | `data/external/acs/<year>/<table>.json` | 2005 to 2024, 19 releases, 19 tables, 2,415,786 estimates; no release for 2020 | 2024 | U.S. government work, public domain |
| Department of Housing and Urban Development, fair market rents and income limits | `data/external/hud` | fiscal years to 2027 (44 years of history), income limits 2004 to 2026 | FY2027, FY2026 | U.S. government work, public domain |
| Freddie Mac, Primary Mortgage Market Survey weekly history | `data/external/pmms` | 2,900 weeks to 2026-10-22 | 2026-10-22 | Free with attribution under Freddie Mac's terms of use; attributed on every page that shows a rate |
| Census Bureau, Building Permits Survey, county and metro files | `data/external/bps` | 2000 to 2025 plus the year to date file (2026 through month 8), 81,768 rows | 2026 through month 8 | U.S. government work, public domain |
| Census Bureau, population estimates with components of change | `data/external/popest` | 2000 to 2025, 3 vintages, 81,714 county rows | 2025 | U.S. government work, public domain |
| Consumer Financial Protection Bureau, HMDA loan level extract | `data/external/hmda/<year>` | 2018 to 2025, 137,678,531 source rows, 64,743,292 after the fetch filter, 55,817,457 in the analysis | 2025 | U.S. government work, public domain; the derived race and ethnicity fields are not loaded |
| Office of Management and Budget, metropolitan delineation files, via the Census Bureau | `data/external/delineations` | 7 vintages to 2,023 | 2,023 | U.S. government work, public domain |
| Census Bureau gazetteer (area names and land area) | `data/external/gazetteer` | latest file | latest | U.S. government work, public domain |

The fetch filter for HMDA, stated once and applied as the files are read: action_taken = 1 and loan_purpose in (1, 31, 32). The analysis filter: occupancy_type = 1 (principal residence); reverse mortgages, open end lines and business purpose loans flagged.

Mortgage rates: Freddie Mac Primary Mortgage Market Survey, used under its terms of use.

Contract digests, which change when a rule or a field changes: FHFA `49ea2f1979a460ca`, ACS `233c33c8be8cdb5c`, HUD `d4b0c640a126f211`, PMMS `ae0e85eaed9be903`, permits `14aadced3de52be7`, population `6201136c93e2ff87`, HMDA `111789025205cb23`, delineations `0688c94ab90f33a8`.
