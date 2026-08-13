-- Separate revenue growth from contribution-margin quality.
select
    month_start,
    net_revenue_eur,
    contribution_margin_eur,
    net_revenue_eur / nullif(lag(net_revenue_eur) over (order by month_start), 0) - 1
        as month_over_month_revenue_growth,
    contribution_margin_rate
    - lag(contribution_margin_rate) over (order by month_start)
        as contribution_margin_rate_change
from finance.mart_monthly_executive
order by month_start;
