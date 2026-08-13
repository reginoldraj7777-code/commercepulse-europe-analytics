-- Additive contribution-margin bridge by quarter.
select
    date_trunc('quarter', month_start)::date as quarter_start,
    sum(net_revenue_eur) as net_revenue_eur,
    -sum(cogs_eur) as cogs_effect_eur,
    sum(recovered_cogs_eur) as recovery_effect_eur,
    -sum(return_handling_cost_eur) as return_handling_effect_eur,
    -sum(fulfillment_cost_eur) as fulfillment_effect_eur,
    -sum(marketing_spend_eur) as marketing_effect_eur,
    sum(contribution_margin_eur) as contribution_margin_eur
from finance.mart_monthly_executive
group by 1
order by 1;
