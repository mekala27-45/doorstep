-- Renter cost burden by household income group (table B25074): seven income groups, each with the renters whose
-- rent takes thirty percent or more and fifty percent or more of income, over renters with a computed share.
{% set groups = [
    ('g_under_10k', 2), ('g_10k_to_20k', 11), ('g_20k_to_35k', 20), ('g_35k_to_50k', 29), ('g_50k_to_75k', 38), ('g_75k_to_100k', 47), ('g_100k_plus', 56)
] %}
with long as (
    select year, cbsa_code, variable, estimate from {{ ref('stg_acs') }} where "table" = 'B25074' and not is_national
),
pivoted as (
    select year, cbsa_code,
        {% for name, start in groups %}
        max(case when variable = 'B25074_{{ '%03d' % start }}' then estimate end) as {{ name }}_total,
        max(case when variable = 'B25074_{{ '%03d' % (start + 4) }}' then estimate end) as {{ name }}_30_35,
        max(case when variable = 'B25074_{{ '%03d' % (start + 5) }}' then estimate end) as {{ name }}_35_40,
        max(case when variable = 'B25074_{{ '%03d' % (start + 6) }}' then estimate end) as {{ name }}_40_50,
        max(case when variable = 'B25074_{{ '%03d' % (start + 7) }}' then estimate end) as {{ name }}_50_plus,
        max(case when variable = 'B25074_{{ '%03d' % (start + 8) }}' then estimate end) as {{ name }}_not_computed{% if not loop.last %},{% endif %}
        {% endfor %}
    from long
    group by year, cbsa_code
)
{% for name, start in groups %}
select year, cbsa_code, '{{ name[2:] }}' as income_group, {{ loop.index }} as group_order,
       {{ name }}_total - coalesce({{ name }}_not_computed, 0) as renters_with_share,
       coalesce({{ name }}_30_35, 0) + coalesce({{ name }}_35_40, 0) + coalesce({{ name }}_40_50, 0) + coalesce({{ name }}_50_plus, 0) as renters_burdened,
       coalesce({{ name }}_50_plus, 0) as renters_severe
from pivoted
{% if not loop.last %}union all{% endif %}
{% endfor %}
