select county_fips, year, vintage, population, births, deaths, international_migration, domestic_migration, intercensal_population
from {{ source('derived', 'popest_county') }}
