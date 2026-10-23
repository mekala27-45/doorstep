-- A county listed twice in one file (two spellings of one name, the same figures) is carried once; the
-- quarantine report keeps the count of the second rows.
select
    year,
    partial_through_month,
    county_fips,
    units_1,
    units_2,
    units_3_4,
    units_5_plus,
    units_total,
    buildings_total,
    value_total,
    units_total_reported
from {{ source('derived', 'bps_county') }}
where not q_county_listed_twice
