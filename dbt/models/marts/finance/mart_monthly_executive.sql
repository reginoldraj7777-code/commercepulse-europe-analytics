with finance as (
    select
        month_start,
        count(distinct order_id) as orders,
        count(distinct customer_key) as purchasing_customers,
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
        sum(allocated_marketing_eur) as marketing_spend_eur,
        sum(contribution_margin_eur) as contribution_margin_eur
    from {{ ref('fct_order_item_profitability') }}
    group by 1
),

sessions as (
    select
        month_start,
        count(distinct session_id) as sessions,
        count(distinct case when converted_order_id is not null then session_id end) as converted_sessions,
        avg(page_load_ms) as average_page_load_ms
    from {{ ref('fct_sessions') }}
    group by 1
),

delivery as (
    select
        date_trunc('month', o.order_ts)::date as month_start,
        count(distinct f.order_id) as fulfilled_orders,
        count(distinct case when f.is_on_time then f.order_id end) as on_time_orders
    from {{ ref('stg_fulfillment') }} as f
    inner join {{ ref('stg_orders') }} as o using (order_id)
    group by 1
),

inventory as (
    select
        date_trunc('month', snapshot_date)::date as month_start,
        count(*) as inventory_snapshots,
        count(*) filter (where stockout_flag) as stockout_snapshots,
        sum(estimated_lost_units) as estimated_lost_units
    from {{ ref('stg_inventory_snapshot') }}
    group by 1
),

targets as (
    select
        month_start,
        sum(net_revenue_target_eur) as net_revenue_target_eur,
        sum(contribution_margin_target_eur) as contribution_margin_target_eur,
        sum(orders_target) as orders_target
    from {{ ref('stg_targets') }}
    group by 1
)

select
    finance.*,
    sessions.sessions,
    sessions.converted_sessions,
    sessions.average_page_load_ms,
    delivery.fulfilled_orders,
    delivery.on_time_orders,
    inventory.inventory_snapshots,
    inventory.stockout_snapshots,
    inventory.estimated_lost_units,
    targets.net_revenue_target_eur,
    targets.contribution_margin_target_eur,
    targets.orders_target,
    {{ safe_divide('sessions.converted_sessions', 'sessions.sessions') }} as conversion_rate,
    {{ safe_divide('finance.net_revenue_eur', 'finance.orders') }} as average_order_value_eur,
    {{ safe_divide('finance.contribution_margin_eur', 'finance.net_revenue_eur') }}
        as contribution_margin_rate,
    {{ safe_divide('finance.units_returned', 'finance.units_sold') }} as return_rate,
    {{ safe_divide('delivery.on_time_orders', 'delivery.fulfilled_orders') }}
        as on_time_delivery_rate,
    {{ safe_divide('inventory.stockout_snapshots', 'inventory.inventory_snapshots') }}
        as stockout_rate,
    {{ safe_divide('finance.net_revenue_eur', 'targets.net_revenue_target_eur') }}
        as net_revenue_target_attainment,
    finance.contribution_margin_eur - targets.contribution_margin_target_eur
        as contribution_margin_variance_eur
from finance
left join sessions using (month_start)
left join delivery using (month_start)
left join inventory using (month_start)
left join targets using (month_start)
