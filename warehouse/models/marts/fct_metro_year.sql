-- The grain: one row per area and year, 2000 to the latest year any source covers. ACS measures are null before
-- 2005 and in 2020 (no one year release); loans are null before 2018. Prices are the anchored value: the
-- all-transactions index moved from the census median value in the anchor year.
with years as (
    select range as year from range(2000, (select max(year) + 1 from {{ ref('int_county_year') }}))
),
dim as (select * from {{ ref('int_metro_dim') }}),
grid as (select d.cbsa_code, y.year from dim d cross join years y),
county as (
    select cbsa_code, year,
           sum(permits) as permits,
           sum(permits_single_family) as permits_single_family,
           sum(permits_5_plus) as permits_5_plus,
           sum(permit_value) as permit_value,
           max(partial_through_month) as permits_partial_through_month,
           sum(population) as population,
           sum(births) as births,
           sum(deaths) as deaths,
           sum(international_migration) as international_migration,
           sum(domestic_migration) as domestic_migration,
           count(*) as counties_mapped
    from {{ ref('int_county_year') }}
    where cbsa_code is not null
    group by cbsa_code, year
),
rates as (
    select year, avg(rate) as rate, count(*) as rate_quarters from {{ ref('stg_rates') }} group by year
),
index_annual as (
    select cbsa_code, year,
           avg(index_nsa) filter (where flavor = 'all-transactions') as index_at,
           avg(index_nsa) filter (where flavor = 'purchase-only') as index_po,
           count(*) filter (where flavor = 'all-transactions') as quarters_at,
           bool_or(rolled_up) as index_rolled_up
    from {{ ref('int_fhfa_area') }}
    group by cbsa_code, year
),
anchor as (
    select a.cbsa_code,
           a.median_value as anchor_value,
           a.median_value_moe as anchor_value_moe,
           i.index_at as anchor_index_at,
           i.index_po as anchor_index_po
    from {{ ref('int_acs_metro_year') }} a
    join index_annual i on i.cbsa_code = a.cbsa_code and i.year = a.year
    where a.year = {{ var('anchor_year') }} and not a.is_national
),
fmr as (
    -- the two bedroom Fair Market Rent, population weighted over the area's counties, by fiscal year
    select m.cbsa_code, f.fiscal_year as year,
           sum(f.fmr_2 * coalesce(p.population, 1)) / sum(coalesce(p.population, 1)) as fmr_2
    from {{ ref('stg_fmr') }} f
    join {{ ref('int_county_vintage_map') }} m on m.county_fips = f.county_fips and m.year = f.fiscal_year
    left join {{ ref('stg_population') }} p on p.county_fips = f.county_fips and p.year = least(f.fiscal_year, (select max(year) from {{ ref('stg_population') }}))
    group by m.cbsa_code, f.fiscal_year
),
il as (
    select m.cbsa_code, i.fiscal_year as year,
           sum(i.median_family_income * coalesce(p.population, 1)) / sum(coalesce(p.population, 1)) as hud_median_family_income,
           sum(i.l80_4 * coalesce(p.population, 1)) / sum(coalesce(p.population, 1)) as hud_low_income_limit_4
    from {{ ref('stg_income_limits') }} i
    join {{ ref('int_county_vintage_map') }} m on m.county_fips = i.county_fips and m.year = i.fiscal_year
    left join {{ ref('stg_population') }} p on p.county_fips = i.county_fips and p.year = least(i.fiscal_year, (select max(year) from {{ ref('stg_population') }}))
    group by m.cbsa_code, i.fiscal_year
)
select
    g.cbsa_code,
    d.cbsa_title,
    d.kind,
    d.states,
    g.year,
    a.year is not null as acs_year_complete,
    a.households, a.households_moe,
    a.owner_households, a.owner_households_moe,
    a.renter_households, a.renter_households_moe,
    a.median_income, a.median_income_moe,
    a.owner_median_income, a.owner_median_income_moe,
    a.renter_median_income, a.renter_median_income_moe,
    a.median_value as median_value_reported, a.median_value_moe as median_value_reported_moe,
    a.median_rent, a.median_rent_moe,
    a.median_rent_share,
    a.housing_units, a.vacant_units, a.vacant_for_rent, a.vacant_for_sale, a.vacant_seasonal,
    a.renters_burdened, a.renters_severe, a.renters_with_share,
    a.renter_burdened_share, a.renter_severe_share,
    a.owners_mortgage_burdened, a.owners_mortgage_with_share, a.owner_mortgage_burdened_share,
    a.owner_mortgage_total as owners_with_mortgage, a.owner_no_mortgage_total as owners_without_mortgage,
    coalesce(a.owner_under_35, 0) + coalesce(a.owner_25_34, 0) as owners_under_35,
    coalesce(a.renter_under_25, 0) + coalesce(a.renter_25_34, 0) as renters_under_35,
    a.units_single_family, a.units_5_plus,
    a.median_real_estate_tax_mortgaged,
    c.permits, c.permits_single_family, c.permits_5_plus, c.permit_value, c.permits_partial_through_month,
    c.population, c.births, c.deaths, c.international_migration, c.domestic_migration, c.counties_mapped,
    r.rate, r.rate_quarters,
    i.index_at, i.index_po, i.quarters_at, i.index_rolled_up,
    an.anchor_value, an.anchor_value_moe,
    case when an.anchor_index_at > 0 then an.anchor_value * i.index_at / an.anchor_index_at end as value_anchored,
    case when an.anchor_index_at > 0 then an.anchor_value_moe * i.index_at / an.anchor_index_at end as value_anchored_moe,
    case when an.anchor_index_po > 0 then an.anchor_value * i.index_po / an.anchor_index_po end as value_anchored_po,
    fm.fmr_2,
    il.hud_median_family_income,
    il.hud_low_income_limit_4,
    l.originations, l.thirty_year_originations, l.low_rate_originations, l.under_3_originations, l.under_3_5_originations,
    l.purchase_loans, l.refinance_loans, l.cash_out_loans,
    l.purchase_median_income, l.purchase_median_value, l.purchase_median_value_to_income, l.purchase_median_loan,
    l.purchase_median_rate, l.purchase_median_rate_spread, l.purchase_p90_rate_spread, l.purchase_median_ltv,
    l.purchase_under_35, l.purchase_with_age, l.purchase_with_income, l.purchase_ltv_over_95, l.purchase_lenders,
    l.refinance_median_rate
from grid g
join dim d using (cbsa_code)
left join {{ ref('int_acs_metro_year') }} a on a.cbsa_code = g.cbsa_code and a.year = g.year and not a.is_national
left join county c on c.cbsa_code = g.cbsa_code and c.year = g.year
left join rates r on r.year = g.year
left join index_annual i on i.cbsa_code = g.cbsa_code and i.year = g.year
left join anchor an on an.cbsa_code = g.cbsa_code
left join fmr fm on fm.cbsa_code = g.cbsa_code and fm.year = g.year
left join il on il.cbsa_code = g.cbsa_code and il.year = g.year
left join {{ ref('int_loans_metro_year') }} l on l.cbsa_code = g.cbsa_code and l.year = g.year
