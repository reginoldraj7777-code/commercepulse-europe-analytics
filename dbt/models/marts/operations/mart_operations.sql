with orders as (
    select
        order_id,
        date_trunc('month', order_ts)::date as month_start,
        market_key
    from {{ ref('stg_orders') }}
    where order_status = 'Completed'
),

delivery as (
    select
        o.month_start,
        o.market_key,
        f.fulfillment_hub,
        f.carrier,
        count(distinct f.order_id) as fulfilled_orders,
        count(distinct case when f.is_on_time then f.order_id end) as on_time_orders,
        avg(f.delivered_date - f.shipped_date) as average_transit_days,
        sum(f.shipping_cost_eur) as shipping_cost_eur
    from orders as o
    inner join {{ ref('stg_fulfillment') }} as f using (order_id)
    group by 1, 2, 3, 4
)

select
    delivery.*,
    m.market_code,
    m.market_name,
    {{ safe_divide('on_time_orders', 'fulfilled_orders') }} as on_time_delivery_rate,
    {{ safe_divide('shipping_cost_eur', 'fulfilled_orders') }} as shipping_cost_per_order_eur
from delivery
left join {{ ref('dim_market') }} as m using (market_key)
