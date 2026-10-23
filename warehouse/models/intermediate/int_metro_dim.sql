-- The metro universe: every area in the latest delineation vintage, with its kind, its counties, its
-- states and its gazetteer centroid. Every other model keys on cbsa_code from here.
with latest as (
    select max(vintage) as vintage from {{ ref('stg_delineations') }}
),
areas as (
    select
        d.cbsa_code,
        any_value(d.cbsa_title) as cbsa_title,
        any_value(d.kind) as kind,
        count(*) as counties,
        string_agg(distinct d.state_name, '; ' order by d.state_name) as states,
        count(distinct d.division_code) filter (where d.division_code is not null) as divisions
    from {{ ref('stg_delineations') }} d
    join latest using (vintage)
    group by d.cbsa_code
)
select
    a.cbsa_code,
    a.cbsa_title,
    a.kind,
    a.counties,
    a.states,
    a.divisions,
    g.latitude,
    g.longitude,
    g.land_sqmi,
    (select vintage from latest) as vintage
from areas a
left join {{ ref('stg_gazetteer') }} g using (cbsa_code)
