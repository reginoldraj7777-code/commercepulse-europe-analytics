-- Compare first-order and repeat-customer economics.
with customer_orders as (
    select
        customer_key,
        order_id,
        min(order_ts) as order_ts,
        sum(net_revenue_eur) as net_revenue_eur,
        sum(contribution_margin_eur) as contribution_margin_eur,
        row_number() over (
            partition by customer_key
            order by min(order_ts), order_id
        ) as customer_order_number
    from finance.fct_order_item_profitability
    group by customer_key, order_id
)

select
    case when customer_order_number = 1 then 'First order' else 'Repeat order' end as order_type,
    count(*) as orders,
    avg(net_revenue_eur) as average_order_value_eur,
    sum(contribution_margin_eur) / nullif(sum(net_revenue_eur), 0)
        as contribution_margin_rate
from customer_orders
group by order_type
order by order_type;
