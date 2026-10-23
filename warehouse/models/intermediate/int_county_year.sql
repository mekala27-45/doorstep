-- Permits and population by county and year, each mapped to its area through the vintage in force that year.
with permits as (
    select year, partial_through_month, county_fips, units_total, units_1, units_5_plus, value_total
    from {{ ref('stg_permits') }}
),
pop as (
    select county_fips, year, population, births, deaths, international_migration, domestic_migration
    from {{ ref('stg_population') }}
),
years as (
    select distinct year from permits union select distinct year from pop
),
base as (
    select y.year, m.county_fips, m.cbsa_code, m.kind, m.vintage
    from years y
    join {{ ref('int_county_vintage_map') }} m using (year)
)
select
    b.year,
    b.county_fips,
    b.cbsa_code,
    b.kind,
    b.vintage,
    p.units_total as permits,
    p.units_1 as permits_single_family,
    p.units_5_plus as permits_5_plus,
    p.value_total as permit_value,
    p.partial_through_month,
    pop.population,
    pop.births,
    pop.deaths,
    pop.international_migration,
    pop.domestic_migration
from base b
left join permits p on p.county_fips = b.county_fips and p.year = b.year
left join pop on pop.county_fips = b.county_fips and pop.year = b.year
