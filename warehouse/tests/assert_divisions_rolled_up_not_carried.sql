-- Every area with divisions carries one series, rolled up; a division code must never appear as an area.
select i.cbsa_code
from {{ ref('int_fhfa_area') }} i
where i.cbsa_code in (select distinct division_code from {{ ref('stg_delineations') }} where division_code is not null)
