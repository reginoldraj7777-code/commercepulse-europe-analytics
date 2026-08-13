-- Find category-channel combinations where discounts undermine contribution.
select
    category,
    channel_name,
    sum(discount_eur) / nullif(sum(gross_revenue_eur), 0) as discount_rate,
    sum(contribution_margin_eur) / nullif(sum(net_revenue_eur), 0)
        as contribution_margin_rate,
    sum(net_revenue_eur) as net_revenue_eur
from finance.fct_order_item_profitability
group by category, channel_name
having sum(net_revenue_eur) > 10000
order by contribution_margin_rate asc, discount_rate desc;
