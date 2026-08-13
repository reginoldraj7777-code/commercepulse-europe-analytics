-- Rolling three-month spend, revenue, and contribution by channel.
select
    month_start,
    channel_name,
    sum(marketing_spend_eur) over (
        partition by channel_name
        order by month_start
        rows between 2 preceding and current row
    ) as rolling_three_month_spend_eur,
    sum(net_revenue_eur) over (
        partition by channel_name
        order by month_start
        rows between 2 preceding and current row
    ) as rolling_three_month_revenue_eur,
    sum(contribution_margin_eur) over (
        partition by channel_name
        order by month_start
        rows between 2 preceding and current row
    ) as rolling_three_month_contribution_eur
from growth.mart_channel_profitability
order by channel_name, month_start;
