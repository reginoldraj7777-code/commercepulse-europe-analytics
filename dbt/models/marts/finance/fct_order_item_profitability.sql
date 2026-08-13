with finance as (
    select
        i.*,
        p.category,
        p.subcategory,
        p.brand,
        m.market_code,
        c.channel_name,
        sum(i.net_revenue_eur) over (
            partition by i.month_start, i.market_key, i.channel_key
        ) as channel_allocation_base_eur,
        sum(i.net_revenue_eur) over (
            partition by i.month_start, i.market_key
        ) as market_allocation_base_eur
    from {{ ref('int_order_item_finance') }} as i
    left join {{ ref('dim_product') }} as p using (product_key)
    left join {{ ref('dim_market') }} as m using (market_key)
    left join {{ ref('dim_channel') }} as c using (channel_key)
),

spend_cells as (
    select
        s.month_start,
        s.market_key,
        s.channel_key,
        s.marketing_spend_eur,
        coalesce(r.channel_net_revenue_eur, 0) as channel_net_revenue_eur,
        case
            when coalesce(r.channel_net_revenue_eur, 0) > 0 then s.marketing_spend_eur
            else 0
        end as direct_spend_eur,
        case
            when coalesce(r.channel_net_revenue_eur, 0) > 0 then 0
            else s.marketing_spend_eur
        end as residual_spend_eur
    from {{ ref('int_marketing_spend_monthly') }} as s
    left join (
        select
            month_start,
            market_key,
            channel_key,
            sum(net_revenue_eur) as channel_net_revenue_eur
        from finance
        group by 1, 2, 3
    ) as r
        on
            s.month_start = r.month_start
            and s.market_key = r.market_key
            and s.channel_key = r.channel_key
),

residual_spend as (
    select
        month_start,
        market_key,
        sum(residual_spend_eur) as residual_spend_eur
    from spend_cells
    group by 1, 2
),

allocated as (
    select
        finance.*,
        coalesce(s.direct_spend_eur, 0)
        * {{ safe_divide('finance.net_revenue_eur', 'finance.channel_allocation_base_eur') }}
            as direct_marketing_allocation_eur,
        coalesce(r.residual_spend_eur, 0)
        * {{ safe_divide('finance.net_revenue_eur', 'finance.market_allocation_base_eur') }}
            as residual_marketing_allocation_eur
    from finance
    left join spend_cells as s
        on
            finance.month_start = s.month_start
            and finance.market_key = s.market_key
            and finance.channel_key = s.channel_key
    left join residual_spend as r
        on
            finance.month_start = r.month_start
            and finance.market_key = r.market_key
)

select
    *,
    direct_marketing_allocation_eur + residual_marketing_allocation_eur
        as allocated_marketing_eur,
    contribution_before_marketing_eur
    - direct_marketing_allocation_eur
    - residual_marketing_allocation_eur
        as contribution_margin_eur,
    {{ safe_divide(
        'contribution_before_marketing_eur - direct_marketing_allocation_eur - residual_marketing_allocation_eur',
        'net_revenue_eur'
    ) }} as contribution_margin_rate
from allocated
