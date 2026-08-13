-- Operational carrier exceptions against explicit SLA and cost thresholds.
select
    month_start,
    market_code,
    fulfillment_hub,
    carrier,
    fulfilled_orders,
    on_time_delivery_rate,
    shipping_cost_per_order_eur,
    case
        when on_time_delivery_rate < 0.90 then 'Critical'
        when on_time_delivery_rate < 0.94 then 'Watch'
        else 'Healthy'
    end as sla_status
from operations.mart_operations
where fulfilled_orders >= 50
order by month_start desc, on_time_delivery_rate asc;
