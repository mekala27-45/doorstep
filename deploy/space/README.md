---
title: doorstep API
sdk: docker
app_port: 8080
pinned: false
license: apache-2.0
short_description: The affordability calculator behind the doorstep story
---

# doorstep API

The affordability calculator and its check log, built from https://github.com/mekala27-45/doorstep by
the repository's `space` workflow. Metro, income, down payment, rate and horizon in; the payment share,
the affordable price, the share of local households that can afford the median home and the rent or buy
breakeven with its interval out, stored in a check log with an audit row and scored when the next quarter
of prices and rates publishes.

Public data from the Federal Housing Finance Agency, the Census Bureau (American Community Survey, Building
Permits Survey, Population Estimates), the Department of Housing and Urban Development and the Consumer
Financial Protection Bureau (HMDA), with mortgage rates from Freddie Mac under its terms of use. Metros are
real and appear as they do in the public record; no household, borrower or address appears. The findings
are a portfolio analysis, not financial advice, not a market forecast and not a fair lending finding.

The Space needs three secrets (DATABASE_URL, DOORSTEP_WRITE_TOKEN, DOORSTEP_DB_SCHEMA) and one variable
(DOORSTEP_CORS_ORIGINS), set in its settings; `docs/serving.md` in the repository says what each one is.
