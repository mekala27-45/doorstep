-- County to area for every publication year, on the latest delineation: a metro is the counties it has now, for
-- every year, so a series never steps where a county moved (the anchored index FHFA publishes is on the same
-- fixed definition). A county the latest delineation no longer carries is one of two things: dropped from every
-- area (it is in the latest population file and maps nowhere) or retired as a code (Connecticut's counties, replaced
-- by planning regions in 2022: absent from the latest population file), and a retired county maps through the
-- last vintage that carried it so its history reaches the area that goes on under the latest code. The area is
-- carried under its latest code through the alias table either way.
with latest as (
    select max(vintage) as vintage from {{ ref('stg_delineations') }}
),
current_counties as (
    select distinct county_fips from {{ ref('stg_population') }}
    where year = (select max(year) from {{ ref('stg_population') }})
),
county_vintage as (
    select d.county_fips,
           max(d.vintage) filter (where d.vintage = (select vintage from latest)) as latest_vintage,
           max(d.vintage) as last_vintage
    from {{ ref('stg_delineations') }} d
    group by d.county_fips
),
chosen as (
    select c.county_fips,
           case when c.latest_vintage is not null then c.latest_vintage
                when cc.county_fips is null then c.last_vintage
           end as vintage,
           case when c.latest_vintage is not null then 'latest'
                when cc.county_fips is null then 'retired county'
                else 'dropped from every area' end as mapping
    from county_vintage c
    left join current_counties cc using (county_fips)
),
years as (
    select range as year from range(2000, 2031)
)
select
    y.year,
    ch.vintage,
    ch.mapping,
    ch.county_fips,
    d.cbsa_code as cbsa_code_vintage,
    d.kind as kind_vintage,
    case when l.cbsa_code is not null then d.cbsa_code else a.latest_code end as cbsa_code,
    coalesce(l.kind, la.kind) as kind,
    d.division_code
from years y
cross join chosen ch
left join {{ ref('stg_delineations') }} d on d.vintage = ch.vintage and d.county_fips = ch.county_fips
left join {{ ref('int_metro_dim') }} l on l.cbsa_code = d.cbsa_code
left join {{ ref('stg_aliases') }} a on a.vintage = d.vintage and a.cbsa_code = d.cbsa_code
left join {{ ref('int_metro_dim') }} la on la.cbsa_code = a.latest_code
