-- The borrower pool at the grain the chapter reads: loans per year, metro, lender and five thousand dollar income bin,
-- with the buyers under 35 and the buyers earning twice the metro median. No loan row is shipped; the median is exact
-- to the bin because the extract reports income in thousands.
select
    year,
    cbsa_code,
    lei,
    cast(floor(income / 5000.0) * 5 as integer) as income_bin,
    count(*) as loans,
    count(*) filter (where under_35) as under_35,
    count(*) filter (where metro_median is not null and income >= 2.0 * metro_median) as over_2x
from {{ ref('int_purchase_loans') }}
where not q_income_exempt_or_missing and income > 0 and kind = 'metropolitan' and metro_median is not null
group by year, cbsa_code, lei, floor(income / 5000.0)
