select year, quarter, period, rate, weeks
from {{ source('derived', 'pmms_quarterly') }}
