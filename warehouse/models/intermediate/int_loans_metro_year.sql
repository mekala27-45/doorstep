-- The HMDA extract rolled to the area and year: counts by purpose, the low rate originations that make up the
-- lock in share, and the borrower pool measures on purchase loans. Loans map to their area through the county
-- and the vintage in force that year; the few with no county code fall back to the reported metro or division.
with loans as (
    select
        l.*,
        coalesce(m.cbsa_code, dv.cbsa_code, l.msa_md) as cbsa_code
    from {{ ref('stg_loans') }} l
    left join {{ ref('int_county_vintage_map') }} m on m.county_fips = l.county_fips and m.year = l.year
    left join (
        select distinct division_code, cbsa_code from {{ ref('stg_delineations') }} where division_code is not null
    ) dv on dv.division_code = l.msa_md
),
purchase as (
    select cbsa_code, year,
           count(*) as purchase_loans,
           quantile_cont(income, 0.5) filter (where not q_income_exempt_or_missing and income > 0) as purchase_median_income,
           quantile_cont(property_value, 0.5) filter (where property_value > 0) as purchase_median_value,
           quantile_cont(property_value / income, 0.5) filter (where not q_income_exempt_or_missing and income > 0 and property_value > 0) as purchase_median_value_to_income,
           quantile_cont(loan_amount, 0.5) as purchase_median_loan,
           quantile_cont(interest_rate, 0.5) filter (where not q_rate_missing) as purchase_median_rate,
           quantile_cont(rate_spread, 0.5) filter (where rate_spread is not null) as purchase_median_rate_spread,
           quantile_cont(rate_spread, 0.9) filter (where rate_spread is not null) as purchase_p90_rate_spread,
           quantile_cont(ltv, 0.5) filter (where ltv is not null and ltv between 1 and 200) as purchase_median_ltv,
           count(*) filter (where applicant_age in ('<25', '25-34')) as purchase_under_35,
           count(*) filter (where applicant_age is not null and applicant_age not in ('8888', '9999')) as purchase_with_age,
           count(*) filter (where not q_income_exempt_or_missing and income > 0) as purchase_with_income,
           count(*) filter (where ltv is not null and ltv > 95) as purchase_ltv_over_95,
           count(distinct lei) as purchase_lenders
    from loans where loan_purpose = 1
    group by cbsa_code, year
),
refinance as (
    select cbsa_code, year,
           count(*) as refinance_loans,
           count(*) filter (where loan_purpose = 32) as cash_out_loans,
           quantile_cont(interest_rate, 0.5) filter (where not q_rate_missing) as refinance_median_rate
    from loans where loan_purpose in (31, 32)
    group by cbsa_code, year
),
low_rate as (
    -- originations under the lock in threshold with a thirty year term, by year, purchase and refinance together
    select cbsa_code, year,
           count(*) filter (where interest_rate < {{ var('lock_in_threshold') }} and not q_rate_missing and not q_term_not_30_years) as low_rate_originations,
           count(*) filter (where interest_rate < 3.0 and not q_rate_missing and not q_term_not_30_years) as under_3_originations,
           count(*) filter (where interest_rate < 3.5 and not q_rate_missing and not q_term_not_30_years) as under_3_5_originations,
           count(*) filter (where not q_term_not_30_years) as thirty_year_originations,
           count(*) as originations
    from loans
    group by cbsa_code, year
)
select
    lr.cbsa_code,
    lr.year,
    lr.originations,
    lr.thirty_year_originations,
    lr.low_rate_originations,
    lr.under_3_originations,
    lr.under_3_5_originations,
    coalesce(p.purchase_loans, 0) as purchase_loans,
    p.purchase_median_income,
    p.purchase_median_value,
    p.purchase_median_value_to_income,
    p.purchase_median_loan,
    p.purchase_median_rate,
    p.purchase_median_rate_spread,
    p.purchase_p90_rate_spread,
    p.purchase_median_ltv,
    p.purchase_under_35,
    p.purchase_with_age,
    p.purchase_with_income,
    p.purchase_ltv_over_95,
    p.purchase_lenders,
    coalesce(r.refinance_loans, 0) as refinance_loans,
    coalesce(r.cash_out_loans, 0) as cash_out_loans,
    r.refinance_median_rate
from low_rate lr
left join purchase p using (cbsa_code, year)
left join refinance r using (cbsa_code, year)
