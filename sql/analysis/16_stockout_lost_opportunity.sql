-- Rank stockout opportunity using an explicitly estimated revenue measure.
select
    date_trunc('quarter', snapshot_date)::date as quarter_start,
    market_code,
    category,
    avg(stockout_flag::integer) as stockout_rate,
    sum(estimated_lost_units) as estimated_lost_units,
    sum(estimated_lost_revenue_eur) as estimated_lost_revenue_eur,
    dense_rank() over (
        partition by date_trunc('quarter', snapshot_date)
        order by sum(estimated_lost_revenue_eur) desc
    ) as opportunity_rank
from operations.fct_inventory
group by date_trunc('quarter', snapshot_date), market_code, category
order by quarter_start, opportunity_rank;
