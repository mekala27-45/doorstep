-- County rows mapped to their area under its latest code, for the metric layer's grain path over permits and
-- population; a county whose area of that year has no latest area is outside this view and every mart.
select year, county_fips, cbsa_code, kind, permits, population, domestic_migration
from {{ ref('int_county_year') }}
where cbsa_code is not null
