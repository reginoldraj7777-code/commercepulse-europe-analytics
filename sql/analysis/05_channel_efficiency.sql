-- Compare channel scale, efficiency, and attributed ROAS.
select
    month_start,
    channel_name,
    orders,
    net_revenue_eur,
    marketing_spend_eur,
    attributed_roas,
    contribution_margin_rate,
    percent_rank() over (
        partition by month_start
        order by contribution_margin_rate
    ) as contribution_percentile
from growth.mart_channel_profitability
order by month_start asc, contribution_margin_rate desc;
