-- Product-market rows that require replenishment review.
select
    snapshot_date,
    market_code,
    product_key,
    category,
    on_hand_units,
    in_transit_units,
    reorder_point_units,
    estimated_lost_units,
    case
        when on_hand_units = 0 then 'Stockout'
        when on_hand_units + in_transit_units < reorder_point_units then 'Below reorder point'
        else 'Covered'
    end as inventory_status
from operations.fct_inventory
where
    on_hand_units = 0
    or on_hand_units + in_transit_units < reorder_point_units
order by snapshot_date desc, estimated_lost_units desc;
