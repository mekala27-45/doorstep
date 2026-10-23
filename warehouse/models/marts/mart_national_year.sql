-- The national rows of the census tables beside the national index and rate, for the aggregate lines.
with acs as (
    select * from {{ ref('int_acs_metro_year') }} where is_national
),
rates as (select year, avg(rate) as rate from {{ ref('stg_rates') }} group by year)
select
    a.year,
    a.households, a.owner_households, a.renter_households,
    a.median_income, a.median_income_moe,
    a.median_value as median_value_reported, a.median_value_moe as median_value_reported_moe,
    a.median_rent, a.median_rent_moe,
    a.renters_burdened, a.renters_severe, a.renters_with_share,
    a.renter_burdened_share, a.renter_severe_share,
    a.renter_median_income, a.owner_median_income,
    r.rate
from acs a
left join rates r using (year)
