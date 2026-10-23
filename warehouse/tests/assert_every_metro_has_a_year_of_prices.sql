-- Every metropolitan area in the dim with census data in the anchor year has an index in the anchor year.
select d.cbsa_code
from {{ ref('int_metro_dim') }} d
join {{ ref('int_acs_metro_year') }} a on a.cbsa_code = d.cbsa_code and a.year = {{ var('anchor_year') }} and not a.is_national
left join {{ ref('int_fhfa_area') }} i on i.cbsa_code = d.cbsa_code and i.year = {{ var('anchor_year') }} and i.flavor = 'all-transactions'
where d.kind = 'metropolitan' and i.cbsa_code is null and a.households > 200000
