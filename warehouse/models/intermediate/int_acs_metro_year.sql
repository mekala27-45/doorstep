-- One row per area and year from the ACS long table: the measures the story reads, estimates and margins.
{% set cells = {
    'households': 'B11001_001',
    'occupied_units': 'B25003_001',
    'owner_households': 'B25003_002',
    'renter_households': 'B25003_003',
    'median_income': 'B19013_001',
    'median_value': 'B25077_001',
    'median_rent': 'B25064_001',
    'median_rent_share': 'B25071_001',
    'owner_median_income': 'B25119_002',
    'renter_median_income': 'B25119_003',
    'housing_units': 'B25001_001',
    'vacant_units': 'B25002_003',
    'vacant_for_rent': 'B25004_002',
    'vacant_for_sale': 'B25004_004',
    'vacant_seasonal': 'B25004_006',
    'rent_share_total': 'B25070_001',
    'rent_share_30_35': 'B25070_007',
    'rent_share_35_40': 'B25070_008',
    'rent_share_40_50': 'B25070_009',
    'rent_share_50_plus': 'B25070_010',
    'rent_share_not_computed': 'B25070_011',
    'owner_mortgage_total': 'B25091_002',
    'owner_mortgage_30_35': 'B25091_008',
    'owner_mortgage_35_40': 'B25091_009',
    'owner_mortgage_40_50': 'B25091_010',
    'owner_mortgage_50_plus': 'B25091_011',
    'owner_mortgage_not_computed': 'B25091_012',
    'owner_no_mortgage_total': 'B25091_013',
    'owner_under_35': 'B25007_003',
    'owner_25_34': 'B25007_004',
    'renter_total_by_age': 'B25007_012',
    'renter_under_25': 'B25007_013',
    'renter_25_34': 'B25007_014',
    'units_single_family': 'B25024_002',
    'units_5_plus_a': 'B25024_006',
    'units_5_plus_b': 'B25024_007',
    'units_5_plus_c': 'B25024_008',
    'units_5_plus_d': 'B25024_009',
    'median_real_estate_tax_mortgaged': 'B25103_002'
} %}
with long as (
    select year, cbsa_code, name, variable, estimate, moe, is_national
    from {{ ref('int_acs_resolved') }}
    where kept
),
pivoted as (
    select
        year,
        cbsa_code,
        any_value(name) as name,
        bool_or(is_national) as is_national,
        {% for alias, var in cells.items() %}
        max(case when variable = '{{ var }}' then estimate end) as {{ alias }},
        max(case when variable = '{{ var }}' then moe end) as {{ alias }}_moe{% if not loop.last %},{% endif %}
        {% endfor %}
    from long
    group by year, cbsa_code
)
select
    *,
    -- renters paying thirty percent or more, and fifty percent or more, over renters with a computed share
    case when rent_share_total - coalesce(rent_share_not_computed, 0) > 0
         then (coalesce(rent_share_30_35, 0) + coalesce(rent_share_35_40, 0) + coalesce(rent_share_40_50, 0) + coalesce(rent_share_50_plus, 0))
              / (rent_share_total - coalesce(rent_share_not_computed, 0)) end as renter_burdened_share,
    case when rent_share_total - coalesce(rent_share_not_computed, 0) > 0
         then coalesce(rent_share_50_plus, 0) / (rent_share_total - coalesce(rent_share_not_computed, 0)) end as renter_severe_share,
    case when owner_mortgage_total - coalesce(owner_mortgage_not_computed, 0) > 0
         then (coalesce(owner_mortgage_30_35, 0) + coalesce(owner_mortgage_35_40, 0) + coalesce(owner_mortgage_40_50, 0) + coalesce(owner_mortgage_50_plus, 0))
              / (owner_mortgage_total - coalesce(owner_mortgage_not_computed, 0)) end as owner_mortgage_burdened_share,
    (coalesce(rent_share_30_35, 0) + coalesce(rent_share_35_40, 0) + coalesce(rent_share_40_50, 0) + coalesce(rent_share_50_plus, 0)) as renters_burdened,
    coalesce(rent_share_50_plus, 0) as renters_severe,
    rent_share_total - coalesce(rent_share_not_computed, 0) as renters_with_share,
    -- margins of error on the sums, combined in quadrature as the census handbook does for a sum of estimates
    sqrt(coalesce(rent_share_30_35_moe, 0) ^ 2 + coalesce(rent_share_35_40_moe, 0) ^ 2 + coalesce(rent_share_40_50_moe, 0) ^ 2 + coalesce(rent_share_50_plus_moe, 0) ^ 2) as renters_burdened_moe,
    coalesce(rent_share_50_plus_moe, 0) as renters_severe_moe,
    sqrt(coalesce(rent_share_total_moe, 0) ^ 2 + coalesce(rent_share_not_computed_moe, 0) ^ 2) as renters_with_share_moe,
    (coalesce(owner_mortgage_30_35, 0) + coalesce(owner_mortgage_35_40, 0) + coalesce(owner_mortgage_40_50, 0) + coalesce(owner_mortgage_50_plus, 0)) as owners_mortgage_burdened,
    owner_mortgage_total - coalesce(owner_mortgage_not_computed, 0) as owners_mortgage_with_share,
    coalesce(units_5_plus_a, 0) + coalesce(units_5_plus_b, 0) + coalesce(units_5_plus_c, 0) + coalesce(units_5_plus_d, 0) as units_5_plus
from pivoted
