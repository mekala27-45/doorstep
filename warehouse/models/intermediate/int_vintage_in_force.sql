-- The delineation vintage in force for each publication year: the latest vintage at or before the year, and
-- the earliest vintage for the years before it. Every source that carries a year resolves its areas through this.
with vintages as (
    select distinct vintage from {{ ref('stg_delineations') }}
),
years as (
    select range as year from range(2000, 2031)
),
in_force as (
    select y.year, max(v.vintage) as vintage
    from years y
    join vintages v on v.vintage <= y.year
    group by y.year
)
select y.year, coalesce(f.vintage, (select min(vintage) from vintages)) as vintage
from years y
left join in_force f using (year)
