-- The county roll up on the latest delineation reproduces the Bureau's published metropolitan and micropolitan
-- population totals of the latest vintage within one tenth of one percent for every area and year both carry:
-- the crosswalk reconciles across the recomposition.
with published as (
    select cbsa_code, year, population
    from {{ ref('stg_population_published') }}
    where vintage = (select max(vintage) from {{ ref('stg_population_published') }})
),
rolled as (
    select cbsa_code, year, sum(population) as population
    from {{ ref('int_county_year') }}
    where cbsa_code is not null
    group by cbsa_code, year
)
select p.cbsa_code, p.year, p.population as published, r.population as rolled_up
from published p
left join rolled r using (cbsa_code, year)
where r.population is null or abs(r.population - p.population) > 0.001 * p.population
