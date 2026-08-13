select
    month_start,
    market_code,
    category,
    subcategory,
    sum(quantity) as units_sold,
    sum(units_returned) as units_returned,
    sum(refund_eur) as refunds_eur,
    sum(handling_cost_eur) as handling_cost_eur,
    sum(recovered_cogs_eur) as recovered_cogs_eur,
    {{ safe_divide('sum(units_returned)', 'sum(quantity)') }} as return_rate,
    sum(contribution_margin_eur) as contribution_margin_eur
from {{ ref('fct_order_item_profitability') }}
group by 1, 2, 3, 4
