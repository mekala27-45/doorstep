-- County rows mapped to their area, for the metric layer's grain path over permits and population.
select year, county_fips, cbsa_code, kind, permits, population, domestic_migration
from {{ ref('int_county_year') }}
where cbsa_code is not null
