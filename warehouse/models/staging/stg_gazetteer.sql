select cbsa_code, name, kind, land_sqmi, latitude, longitude, gazetteer_year
from {{ source('derived', 'gazetteer') }}
