select
    order_item_id,
    sum(units_returned) as units_returned,
    sum(refund_eur) as refund_eur,
    sum(handling_cost_eur) as handling_cost_eur,
    sum(recovered_cogs_eur) as recovered_cogs_eur,
    max(return_date) as latest_return_date
from {{ ref('stg_returns') }}
group by order_item_id
