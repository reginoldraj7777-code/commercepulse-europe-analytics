with completed_orders as (
    select *
    from {{ ref('stg_orders') }}
    where order_status = 'Completed'
),

items as (
    select
        i.order_item_id,
        i.order_id,
        i.product_key,
        i.quantity,
        i.gross_revenue_eur,
        i.discount_eur,
        i.cogs_eur,
        o.session_id,
        o.customer_key,
        o.market_key,
        o.channel_key,
        o.campaign_key,
        o.order_ts,
        date_trunc('month', o.order_ts)::date as month_start,
        count(*) over (partition by i.order_id) as order_item_count
    from {{ ref('stg_order_items') }} as i
    inner join completed_orders as o using (order_id)
),

with_returns as (
    select
        items.*,
        coalesce(r.units_returned, 0) as units_returned,
        coalesce(r.refund_eur, 0) as refund_eur,
        coalesce(r.handling_cost_eur, 0) as handling_cost_eur,
        coalesce(r.recovered_cogs_eur, 0) as recovered_cogs_eur
    from items
    left join {{ ref('int_returns_by_item') }} as r using (order_item_id)
),

with_fulfillment as (
    select
        with_returns.*,
        coalesce(f.shipping_cost_eur, 0)
        / nullif(with_returns.order_item_count, 0) as allocated_shipping_cost_eur
    from with_returns
    left join {{ ref('stg_fulfillment') }} as f using (order_id)
)

select
    *,
    gross_revenue_eur - discount_eur - refund_eur as net_revenue_eur,
    gross_revenue_eur - discount_eur - refund_eur - cogs_eur
    + recovered_cogs_eur - handling_cost_eur - allocated_shipping_cost_eur
        as contribution_before_marketing_eur
from with_fulfillment
