-- Compare hub reliability with cost per fulfilled order.
select
    month_start,
    fulfillment_hub,
    sum(fulfilled_orders) as fulfilled_orders,
    sum(on_time_orders)::double precision / nullif(sum(fulfilled_orders), 0)
        as on_time_delivery_rate,
    sum(shipping_cost_eur) / nullif(sum(fulfilled_orders), 0)
        as shipping_cost_per_order_eur,
    avg(average_transit_days) as average_transit_days
from operations.mart_operations
group by month_start, fulfillment_hub
order by month_start, on_time_delivery_rate;
