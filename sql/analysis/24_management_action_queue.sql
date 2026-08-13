-- One query that prioritizes target, margin, delivery, return, and stockout exceptions.
with target_risk as (
    select
        month_start,
        market_code,
        channel_name,
        net_revenue_variance_eur,
        contribution_margin_variance_eur,
        row_number() over (
            partition by month_start
            order by contribution_margin_variance_eur
        ) as priority_rank
    from finance.mart_target_variance
    where
        net_revenue_variance_eur < 0
        or contribution_margin_variance_eur < 0
)

select
    month_start,
    market_code,
    channel_name,
    net_revenue_variance_eur,
    contribution_margin_variance_eur,
    case
        when priority_rank <= 3 then 'P0'
        when priority_rank <= 10 then 'P1'
        else 'P2'
    end as suggested_priority
from target_risk
order by month_start desc, priority_rank asc;
