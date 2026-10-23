-- The Bureau's own metropolitan and micropolitan totals from the population estimates files, by vintage, the
-- check on the county roll up (a reconciliation, never a source of the marts).
select cbsa_code, year, vintage, population, births, deaths, international_migration, domestic_migration
from {{ source('derived', 'popest_metro_published') }}
