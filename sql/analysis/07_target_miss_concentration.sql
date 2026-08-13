-- Quantify how much of the revenue target miss is concentrated in the worst cells.
with misses as (
    select
        month_start,
        market_code,
        channel_name,
        net_revenue_variance_eur,
        row_number() over (
            partition by month_start
            order by net_revenue_variance_eur
        ) as miss_rank
    from finance.mart_target_variance
    where net_revenue_variance_eur < 0
)

select
    month_start,
    sum(net_revenue_variance_eur) filter (where miss_rank <= 5) as top_five_miss_eur,
    sum(net_revenue_variance_eur) as total_miss_eur,
    sum(net_revenue_variance_eur) filter (where miss_rank <= 5)
    / nullif(sum(net_revenue_variance_eur), 0) as top_five_share
from misses
group by month_start
order by month_start;
