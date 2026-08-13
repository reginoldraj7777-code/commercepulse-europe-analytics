select *
from {{ ref('mart_monthly_executive') }}
where conversion_rate not between 0 and 1
    or contribution_margin_rate not between -1 and 1
    or return_rate not between 0 and 1
    or on_time_delivery_rate not between 0 and 1
    or stockout_rate not between 0 and 1
