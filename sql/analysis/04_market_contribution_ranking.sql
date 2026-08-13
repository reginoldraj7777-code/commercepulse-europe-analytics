-- Rank markets on revenue and contribution margin without averaging ratios.
select
    market_code,
    sum(net_revenue_eur) as net_revenue_eur,
    sum(contribution_margin_eur) as contribution_margin_eur,
    sum(contribution_margin_eur) / nullif(sum(net_revenue_eur), 0)
        as contribution_margin_rate,
    dense_rank() over (order by sum(contribution_margin_eur) desc)
        as contribution_rank
from finance.fct_order_item_profitability
group by market_code
order by contribution_rank;
