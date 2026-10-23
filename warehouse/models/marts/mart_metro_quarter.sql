-- The quarterly series: the index, the anchored value, the quarter's rate and the payment on the median home,
-- with the price part and the rate part of the payment change decomposed against the anchor quarter.
with q as (
    select i.cbsa_code, i.flavor, i.year, i.quarter, i.period, i.index_nsa, i.index_sa, i.rolled_up
    from {{ ref('int_fhfa_area') }} i
    where i.flavor = 'all-transactions'
),
anchor as (
    select cbsa_code, anchor_value, anchor_index_at
    from (
        select distinct cbsa_code, anchor_value, index_at as anchor_index_at
        from {{ ref('fct_metro_year') }}
        where year = {{ var('anchor_year') }} and anchor_value is not null and index_at is not null
    )
),
income as (
    select cbsa_code, year, median_income from {{ ref('fct_metro_year') }} where median_income is not null
),
income_filled as (
    -- the latest census income at or before the quarter's year (2020 has none, the latest year may not yet)
    select q.cbsa_code, q.year, q.quarter,
           (select i.median_income from income i where i.cbsa_code = q.cbsa_code and i.year <= q.year order by i.year desc limit 1) as median_income,
           (select i.year from income i where i.cbsa_code = q.cbsa_code and i.year <= q.year order by i.year desc limit 1) as income_year
    from q
)
select
    q.cbsa_code,
    d.cbsa_title,
    d.kind,
    q.year, q.quarter, q.period,
    q.index_nsa, q.rolled_up,
    r.rate,
    a.anchor_value * q.index_nsa / a.anchor_index_at as value_anchored,
    {{ monthly_payment('a.anchor_value * q.index_nsa / a.anchor_index_at * (1.0 - ' ~ var('down_payment_share') ~ ')', 'r.rate', var('loan_term_years')) }} as payment,
    inc.median_income, inc.income_year,
    case when inc.median_income > 0 then 12.0 * {{ monthly_payment('a.anchor_value * q.index_nsa / a.anchor_index_at * (1.0 - ' ~ var('down_payment_share') ~ ')', 'r.rate', var('loan_term_years')) }} / inc.median_income end as payment_share
from q
join {{ ref('int_metro_dim') }} d using (cbsa_code)
left join anchor a using (cbsa_code)
left join {{ ref('stg_rates') }} r on r.year = q.year and r.quarter = q.quarter
left join income_filled inc on inc.cbsa_code = q.cbsa_code and inc.year = q.year and inc.quarter = q.quarter
