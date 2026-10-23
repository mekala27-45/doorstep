-- The analysis rows of the HMDA extract: principal residences, not reverse, open end or business loans, metro resolved.
select
    year,
    lei,
    msa_md,
    state_code,
    county_fips,
    loan_purpose,
    lien_status,
    loan_amount,
    property_value,
    income,
    interest_rate,
    rate_spread,
    loan_term,
    ltv,
    dti_band,
    applicant_age,
    total_units,
    msa_md_median_family_income,
    q_income_exempt_or_missing,
    q_rate_missing,
    q_term_not_30_years
from {{ source('loans', 'lar') }}
where not q_not_principal_residence and not q_reverse_open_or_business and not q_metro_unresolved
