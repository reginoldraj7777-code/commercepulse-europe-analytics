-- Monthly profitable-growth scorecard with target variance.
select
    month_start,
    net_revenue_eur,
    contribution_margin_eur,
    contribution_margin_rate,
    conversion_rate,
    return_rate,
    on_time_delivery_rate,
    stockout_rate,
    net_revenue_target_attainment,
    contribution_margin_variance_eur
from finance.mart_monthly_executive
order by month_start;
