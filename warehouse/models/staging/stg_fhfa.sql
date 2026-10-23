-- The price index rows that passed every quarantine rule, with the flag kept for the data page.
select
    place_id,
    place_name,
    flavor,
    year,
    quarter,
    period,
    index_nsa,
    index_sa,
    is_division,
    quarantined
from {{ source('derived', 'fhfa_quarterly') }}
