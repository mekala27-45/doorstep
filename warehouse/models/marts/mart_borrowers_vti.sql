-- Property value over borrower income per year and lender in quarter point bins, for the median value to income ratio.
select
    year,
    lei,
    floor(property_value / income / 0.25) * 0.25 as vti_bin,
    count(*) as loans
from {{ ref('int_purchase_loans') }}
where not q_income_exempt_or_missing and income > 0 and property_value > 0 and property_value / income <= 20 and kind = 'metropolitan'
group by year, lei, floor(property_value / income / 0.25)
