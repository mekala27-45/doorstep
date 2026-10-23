-- The price index per area and quarter, all-transactions as the primary series and purchase-only beside it.
-- The eleven areas FHFA publishes as metropolitan divisions are rolled up: the area's quarterly log change is
-- the population weighted mean of its divisions' log changes, with the weights the divisions' county
-- population in the anchor year, and the chain starts at 100 in the first quarter every division covers.
with latest as (select max(vintage) as vintage from {{ ref('stg_delineations') }}),
division_counties as (
    select d.division_code, d.cbsa_code, d.county_fips
    from {{ ref('stg_delineations') }} d join latest using (vintage)
    where d.division_code is not null
),
weights as (
    select dc.division_code, dc.cbsa_code, sum(p.population) as population
    from division_counties dc
    join {{ ref('stg_population') }} p on p.county_fips = dc.county_fips and p.year = {{ var('anchor_year') }}
    group by dc.division_code, dc.cbsa_code
),
clean as (
    select * from {{ ref('stg_fhfa') }} where not quarantined
),
whole as (
    select place_id as cbsa_code, place_name, flavor, year, quarter, period, index_nsa, index_sa, false as rolled_up
    from clean where not is_division
),
division_changes as (
    select
        c.place_id as division_code,
        w.cbsa_code,
        w.population,
        c.flavor, c.year, c.quarter, c.period,
        ln(c.index_nsa) - ln(lag(c.index_nsa) over (partition by c.place_id, c.flavor order by c.year, c.quarter)) as dlog
    from clean c
    join weights w on w.division_code = c.place_id
    where c.is_division
),
area_changes as (
    -- a quarter counts only when every division of the area has a change that quarter
    select cbsa_code, flavor, year, quarter, period,
           sum(dlog * population) / sum(population) as dlog,
           count(*) as divisions_present,
           (select count(*) from weights w2 where w2.cbsa_code = dc.cbsa_code) as divisions_total
    from division_changes dc
    where dlog is not null
    group by cbsa_code, flavor, year, quarter, period
),
chained as (
    select cbsa_code, flavor, year, quarter, period,
           100.0 * exp(sum(dlog) over (partition by cbsa_code, flavor order by year, quarter rows unbounded preceding)) as index_nsa
    from area_changes
    where divisions_present = divisions_total
),
rolled as (
    select ch.cbsa_code,
           m.cbsa_title as place_name,
           ch.flavor, ch.year, ch.quarter, ch.period, ch.index_nsa,
           cast(null as double) as index_sa,
           true as rolled_up
    from chained ch
    join {{ ref('int_metro_dim') }} m using (cbsa_code)
)
select * from whole
union all
select * from rolled
