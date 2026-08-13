-- Segment purchasing customers into contribution-value deciles.
with customer_value as (
    select
        customer_key,
        count(distinct order_id) as orders,
        sum(net_revenue_eur) as net_revenue_eur,
        sum(contribution_margin_eur) as contribution_margin_eur
    from finance.fct_order_item_profitability
    group by customer_key
),

deciled as (
    select
        *,
        ntile(10) over (order by contribution_margin_eur desc) as contribution_decile
    from customer_value
)

select
    contribution_decile,
    count(*) as customers,
    avg(orders) as average_orders,
    sum(net_revenue_eur) as net_revenue_eur,
    sum(contribution_margin_eur) as contribution_margin_eur
from deciled
group by contribution_decile
order by contribution_decile;
