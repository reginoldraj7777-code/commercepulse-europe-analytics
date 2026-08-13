select
    month_start,
    market_key,
    market_code,
    channel_key,
    channel_name,
    count(distinct order_id) as orders,
    count(distinct customer_key) as purchasing_customers,
    sum(net_revenue_eur) as net_revenue_eur,
    sum(allocated_marketing_eur) as marketing_spend_eur,
    sum(contribution_margin_eur) as contribution_margin_eur,
    {{ safe_divide('sum(contribution_margin_eur)', 'sum(net_revenue_eur)') }}
        as contribution_margin_rate,
    {{ safe_divide('sum(net_revenue_eur)', 'sum(allocated_marketing_eur)') }}
        as attributed_roas
from {{ ref('fct_order_item_profitability') }}
group by 1, 2, 3, 4, 5
