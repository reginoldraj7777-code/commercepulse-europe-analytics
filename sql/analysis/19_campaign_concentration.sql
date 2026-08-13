-- Identify dependence on a small set of paid campaigns.
with campaign_value as (
    select
        campaign_key,
        sum(net_revenue_eur) as net_revenue_eur,
        sum(contribution_margin_eur) as contribution_margin_eur
    from finance.fct_order_item_profitability
    where campaign_key > 0
    group by campaign_key
),

ranked as (
    select
        *,
        row_number() over (order by contribution_margin_eur desc) as contribution_rank,
        sum(contribution_margin_eur) over (order by contribution_margin_eur desc)
        / nullif(sum(contribution_margin_eur) over (), 0) as cumulative_contribution_share
    from campaign_value
)

select *
from ranked
order by contribution_rank;
