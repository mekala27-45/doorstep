-- County to area, per vintage, and the vintage in force for each publication year of each source.
-- The census, the permits and the population files carry the vintage current when they were released;
-- mapping a county through the wrong vintage puts it in the wrong metro, so the year decides.
with vintages as (
    select distinct vintage from {{ ref('stg_delineations') }}
),
years as (
    select range as year from range(2000, 2031)
),
in_force as (
    -- the latest vintage whose year is at or before the publication year
    select y.year, max(v.vintage) as vintage
    from years y
    join vintages v on v.vintage <= y.year
    group by y.year
),
filled as (
    select y.year, coalesce(f.vintage, (select min(vintage) from vintages)) as vintage
    from years y
    left join in_force f using (year)
)
select
    f.year,
    f.vintage,
    d.county_fips,
    d.cbsa_code,
    d.kind,
    d.division_code
from filled f
join {{ ref('stg_delineations') }} d using (vintage)
