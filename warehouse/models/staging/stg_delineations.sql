select vintage, cbsa_code, cbsa_title, kind, division_code, division_title, county_fips, county_name, state_name, central
from {{ source('derived', 'delineations') }}
where not quarantined
