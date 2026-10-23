-- Jam values become nulls here; the quarantine report keeps the count. Everything else passes as published.
select
    year,
    cbsa_code,
    name,
    "table",
    variable,
    case when q_jam_value then null else estimate end as estimate,
    case when q_jam_value or q_negative_moe then null else moe end as moe,
    source,
    is_national
from {{ source('derived', 'acs_long') }}
