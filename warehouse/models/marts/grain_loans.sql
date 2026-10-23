-- Loan rows mapped to their area, for the metric layer's grain path (the mart aggregates the same rows).
select
    l.year,
    coalesce(m.cbsa_code, dv.cbsa_code, l.msa_md) as cbsa_code,
    d.kind,
    l.loan_purpose,
    l.interest_rate,
    l.q_rate_missing,
    l.q_term_not_30_years
from {{ ref('stg_loans') }} l
left join {{ ref('int_county_vintage_map') }} m on m.county_fips = l.county_fips and m.year = l.year
left join (select distinct division_code, cbsa_code from {{ ref('stg_delineations') }} where division_code is not null) dv on dv.division_code = l.msa_md
join {{ ref('int_metro_dim') }} d on d.cbsa_code = coalesce(m.cbsa_code, dv.cbsa_code, l.msa_md)
