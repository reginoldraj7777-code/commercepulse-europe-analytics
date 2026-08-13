-- Pareto view of return reasons by refund value.
with reasons as (
    select
        return_reason,
        sum(refund_eur) as refund_eur
    from staging.stg_returns
    group by return_reason
),

ranked as (
    select
        *,
        sum(refund_eur) over (order by refund_eur desc) as cumulative_refund_eur,
        sum(refund_eur) over () as total_refund_eur
    from reasons
)

select
    *,
    cumulative_refund_eur / nullif(total_refund_eur, 0) as cumulative_refund_share
from ranked
order by refund_eur desc;
