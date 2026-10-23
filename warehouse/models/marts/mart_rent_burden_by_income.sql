-- Renter cost burden by household income group (table B25074): seven income groups, each with the renters whose
-- rent takes thirty percent or more and fifty percent or more of income, over renters with a computed share.
-- The table carried five rent bands (seven cells per group, fifty in all) through the 2013 release and seven bands
-- (nine cells per group, sixty four in all) from the 2014 release; the fifty percent band exists only from 2014, so
-- the severe count is null before that and the chart that crosses it says so.
{% set groups = ['under_10k', '10k_to_20k', '20k_to_35k', '35k_to_50k', '50k_to_75k', '75k_to_100k', '100k_plus'] %}
with long as (
    select year, cbsa_code, cast(substr(variable, 8, 3) as integer) as cell, estimate
    from {{ ref('stg_acs') }} where "table" = 'B25074' and not is_national
),
cells as (
    select year, cbsa_code, cell, estimate,
           case when year <= 2013 then 7 else 9 end as per_group,
           (cell - 2) // case when year <= 2013 then 7 else 9 end as group_index,
           (cell - 2) % case when year <= 2013 then 7 else 9 end as cell_offset
    from long where cell >= 2
),
pivoted as (
    select year, cbsa_code, group_index, max(per_group) as per_group,
           max(case when cell_offset = 0 then estimate end) as total,
           max(case when cell_offset = per_group - 1 then estimate end) as not_computed,
           sum(case when per_group = 7 and cell_offset in (4, 5) then estimate end) as burdened_old,
           sum(case when per_group = 9 and cell_offset in (4, 5, 6, 7) then estimate end) as burdened_new,
           max(case when per_group = 9 and cell_offset = 7 then estimate end) as severe_new
    from cells
    group by year, cbsa_code, group_index
)
select
    year,
    cbsa_code,
    case group_index
        {% for name in groups %}
        when {{ loop.index0 }} then '{{ name }}'
        {% endfor %}
    end as income_group,
    group_index + 1 as group_order,
    total - coalesce(not_computed, 0) as renters_with_share,
    coalesce(burdened_new, burdened_old, 0) as renters_burdened,
    case when per_group = 9 then coalesce(severe_new, 0) end as renters_severe
from pivoted
where group_index between 0 and 6
