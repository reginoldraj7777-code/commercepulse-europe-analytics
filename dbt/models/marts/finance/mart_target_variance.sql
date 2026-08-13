with actuals as (
    select
        month_start,
        market_key,
        channel_key,
        count(distinct order_id) as actual_orders,
        sum(net_revenue_eur) as actual_net_revenue_eur,
        sum(contribution_margin_eur) as actual_contribution_margin_eur
    from {{ ref('fct_order_item_profitability') }}
    group by 1, 2, 3
),

targets as (
    select * from {{ ref('stg_targets') }}
)

select
    targets.month_start,
    targets.market_key,
    targets.channel_key,
    m.market_code,
    c.channel_name,
    coalesce(actuals.actual_orders, 0) as actual_orders,
    targets.orders_target,
    coalesce(actuals.actual_net_revenue_eur, 0) as actual_net_revenue_eur,
    targets.net_revenue_target_eur,
    coalesce(actuals.actual_net_revenue_eur, 0) - targets.net_revenue_target_eur
        as net_revenue_variance_eur,
    {{ safe_divide('coalesce(actuals.actual_net_revenue_eur, 0)', 'targets.net_revenue_target_eur') }}
        as net_revenue_target_attainment,
    coalesce(actuals.actual_contribution_margin_eur, 0) as actual_contribution_margin_eur,
    targets.contribution_margin_target_eur,
    coalesce(actuals.actual_contribution_margin_eur, 0)
    - targets.contribution_margin_target_eur as contribution_margin_variance_eur
from targets
left join actuals using (month_start, market_key, channel_key)
left join {{ ref('dim_market') }} as m using (market_key)
left join {{ ref('dim_channel') }} as c using (channel_key)
