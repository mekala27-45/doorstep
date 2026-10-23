-- The FMR history when present (every fiscal year), the latest fiscal year's file otherwise.
{% set history = "../data/derived/hud_fmr_history.parquet" %}
select county_fips, fiscal_year, fmr_0, fmr_1, fmr_2, fmr_3, fmr_4
from {{ source('derived', 'hud_fmr_history') }}
