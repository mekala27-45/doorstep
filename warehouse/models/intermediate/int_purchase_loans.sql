-- Purchase loans on principal residences with the metro median household income of the nearest census year beside
-- them, for the borrower pool histograms. The census has no 2020 release, so 2020 loans are compared with 2019 incomes.
with loans as (
    select
        l.year, l.lei, l.income, l.property_value, l.rate_spread, l.applicant_age, l.q_income_exempt_or_missing,
        coalesce(m.cbsa_code, dv.cbsa_code, l.msa_md) as cbsa_code
    from {{ ref('stg_loans') }} l
    left join {{ ref('int_county_vintage_map') }} m on m.county_fips = l.county_fips and m.year = l.year
    left join (select distinct division_code, cbsa_code from {{ ref('stg_delineations') }} where division_code is not null) dv on dv.division_code = l.msa_md
    where l.loan_purpose = 1
),
incomes as (
    select cbsa_code, year, median_income from {{ ref('int_acs_metro_year') }} where median_income is not null and not is_national
),
nearest as (
    select l.year as loan_year, l.cbsa_code,
           arg_min(i.median_income, abs(i.year - l.year) * 2 + case when i.year > l.year then 1 else 0 end) as metro_median
    from (select distinct year, cbsa_code from loans) l
    join incomes i on i.cbsa_code = l.cbsa_code
    group by l.year, l.cbsa_code
)
select
    l.year, l.lei, l.cbsa_code, d.kind,
    l.income, l.property_value, l.rate_spread,
    l.applicant_age in ('<25', '25-34') as under_35,
    n.metro_median,
    l.q_income_exempt_or_missing
from loans l
join {{ ref('int_metro_dim') }} d on d.cbsa_code = l.cbsa_code
left join nearest n on n.cbsa_code = l.cbsa_code and n.loan_year = l.year
