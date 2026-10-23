-- The rate spread distribution of purchase loans by year, in eighth point bins.
select
    year,
    floor(rate_spread / 0.125) * 0.125 as spread_bin,
    count(*) as loans
from {{ ref('int_purchase_loans') }}
where rate_spread is not null and rate_spread between -5 and 15 and kind = 'metropolitan'
group by year, floor(rate_spread / 0.125)
