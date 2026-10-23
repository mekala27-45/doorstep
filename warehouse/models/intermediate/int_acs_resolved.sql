-- The census long table with every area carried under its latest code. A release carries the codes of the
-- vintage in force that year; a code with an alias resolves to the latest area, a code without one stays
-- outside the metro universe. When a merged area and the area that absorbed it both publish in one year, the
-- absorbing area's row is the one kept (kept = false marks the other, counted by the warehouse tests), so the
-- latest area has one row per year and its series carries a step where the merge happened.
with rows_ as (
    select a.year, a.cbsa_code as cbsa_code_published, a.name, a."table", a.variable, a.estimate, a.moe, a.source, a.is_national,
           case when a.is_national then a.cbsa_code
                when l.cbsa_code is not null then a.cbsa_code
                else al.latest_code end as cbsa_code,
           case when l.cbsa_code is not null then 0 else 1 end as alias_rank,
           coalesce(al.counties_in_latest, 0) as counties_in_latest
    from {{ ref('stg_acs') }} a
    left join {{ ref('int_vintage_in_force') }} f on f.year = a.year
    left join {{ ref('int_metro_dim') }} l on l.cbsa_code = a.cbsa_code
    left join {{ ref('stg_aliases') }} al on al.vintage = f.vintage and al.cbsa_code = a.cbsa_code
),
ranked as (
    select *,
           row_number() over (partition by year, cbsa_code, variable, is_national
                              order by alias_rank, counties_in_latest desc, cbsa_code_published) as rank_in_area
    from rows_
    where cbsa_code is not null
)
select year, cbsa_code, cbsa_code_published, name, "table", variable, estimate, moe, source, is_national,
       rank_in_area = 1 as kept
from ranked
