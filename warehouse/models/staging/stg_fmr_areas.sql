select county_fips, fiscal_year, hud_area_code, hud_area_name, cbsa_code, fmr_2
from {{ source('derived', 'hud_fmr_latest') }}
