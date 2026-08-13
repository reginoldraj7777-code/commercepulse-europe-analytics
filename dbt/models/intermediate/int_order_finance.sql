select
    order_id,
    min(order_ts) as order_ts,
    min(month_start) as month_start,
    min(customer_key) as customer_key,
    min(market_key) as market_key,
    min(channel_key) as channel_key,
    sum(quantity) as units_sold,
    sum(units_returned) as units_returned,
    sum(gross_revenue_eur) as gross_revenue_eur,
    sum(discount_eur) as discounts_eur,
    sum(refund_eur) as refunds_eur,
    sum(net_revenue_eur) as net_revenue_eur,
    sum(cogs_eur) as cogs_eur,
    sum(recovered_cogs_eur) as recovered_cogs_eur,
    sum(handling_cost_eur) as return_handling_cost_eur,
    sum(allocated_shipping_cost_eur) as fulfillment_cost_eur,
    sum(contribution_before_marketing_eur) as contribution_before_marketing_eur
from {{ ref('int_order_item_finance') }}
group by order_id
