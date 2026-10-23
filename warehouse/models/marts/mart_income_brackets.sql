-- Households by income bracket (table B19001), one row per area, year and bracket, for the affordable share.
select
    a.year,
    a.cbsa_code,
    cast(substr(a.variable, 8, 3) as integer) - 2 as bracket,
    a.estimate as households,
    a.moe as households_moe
from {{ ref('stg_acs') }} a
where a."table" = 'B19001' and a.variable <> 'B19001_001' and not a.is_national
