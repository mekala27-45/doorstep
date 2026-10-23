-- In the anchor year the anchored value equals the census median value (the index is a movement, the
-- census is the level): any area where they differ by more than a dollar means the anchor is wrong.
select cbsa_code, year, value_anchored, median_value_reported
from {{ ref('fct_metro_year') }}
where year = {{ var('anchor_year') }}
  and value_anchored is not null
  and abs(value_anchored - median_value_reported) > 1.0
