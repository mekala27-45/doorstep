-- The census long table restricted to the metro universe (every area under its latest code, the rows the
-- metro year keeps), with the area's kind, for the metric layer's grain path.
select a.year, a.cbsa_code, d.kind, a."table", a.variable, a.estimate, a.moe
from {{ ref('int_acs_resolved') }} a
join {{ ref('int_metro_dim') }} d using (cbsa_code)
where not a.is_national and a.kept
