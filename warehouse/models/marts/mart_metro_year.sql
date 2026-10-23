-- The shipped metro by year mart: the grain plus the derived measures every surface reads, with the payment and
-- the shares computed once here. Twelve payments at the year's average rate on ninety percent of the anchored
-- value, over the median household income.
select
    f.*,
    {{ monthly_payment('f.value_anchored * (1.0 - ' ~ var('down_payment_share') ~ ')', 'f.rate', var('loan_term_years')) }} as payment,
    case when f.median_income > 0 then 12.0 * {{ monthly_payment('f.value_anchored * (1.0 - ' ~ var('down_payment_share') ~ ')', 'f.rate', var('loan_term_years')) }} / f.median_income end as payment_share,
    case when f.median_income > 0 then f.value_anchored / f.median_income end as price_to_income,
    case when f.median_income > 0 then 12.0 * f.median_rent / f.median_income end as rent_share_of_median_income,
    case when f.value_anchored > 0 then 12.0 * f.median_rent / f.value_anchored end as rent_to_price,
    case when f.population > 0 then 100.0 * f.domestic_migration / f.population end as domestic_migration_per_100,
    case when f.population > 0 then 1000.0 * f.permits / f.population end as permits_per_1000_residents,
    case when f.owner_households > 0 then 100.0 * f.purchase_loans / f.owner_households end as turnover_per_100_owners,
    case when f.purchase_with_age > 0 then f.purchase_under_35::double / f.purchase_with_age end as purchase_under_35_share,
    case when f.median_income > 0 then f.purchase_median_income / f.median_income end as borrower_income_ratio
from {{ ref('fct_metro_year') }} f
