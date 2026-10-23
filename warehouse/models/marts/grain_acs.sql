-- The census long table restricted to the metro universe, with the area's kind, for the metric layer's grain path.
select a.year, a.cbsa_code, d.kind, a."table", a.variable, a.estimate, a.moe
from {{ ref('stg_acs') }} a
join {{ ref('int_metro_dim') }} d using (cbsa_code)
where not a.is_national
