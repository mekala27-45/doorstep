-- Every area code of an earlier vintage that is not a latest code, with the latest area that holds more than
-- half of its counties (recode: the area went on under a new code; merged: absorbed into a neighbour) or no
-- alias at all (dissolved, split). Derived from the delineation files by the data stage.
select vintage, cbsa_code, cbsa_title, latest_code, latest_title, counties, counties_in_latest, rule
from {{ source('derived', 'area_aliases') }}
