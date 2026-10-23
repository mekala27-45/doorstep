-- Every alias points at a code of the latest vintage, and an earlier code resolves to the same latest area in
-- every vintage that carries it.
with bad_target as (
    select a.cbsa_code
    from {{ ref('stg_aliases') }} a
    left join {{ ref('int_metro_dim') }} d on d.cbsa_code = a.latest_code
    where a.latest_code is not null and d.cbsa_code is null
),
two_targets as (
    select cbsa_code
    from {{ ref('stg_aliases') }}
    where latest_code is not null
    group by cbsa_code
    having count(distinct latest_code) > 1
)
select * from bad_target
union all
select * from two_targets
