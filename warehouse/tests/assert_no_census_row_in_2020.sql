-- The census published no one year release for 2020; a row there means something filled the gap.
select year, cbsa_code from {{ ref('fct_metro_year') }} where year = 2020 and acs_year_complete
