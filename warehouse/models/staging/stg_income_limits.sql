select county_fips, fiscal_year, hud_area_code, hud_area_name, cbsa_code, median_family_income, l30_4, l50_4, l80_4
from {{ source('derived', 'hud_income_limits') }}
where not quarantined
