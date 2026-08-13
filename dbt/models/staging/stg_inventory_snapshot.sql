select
    inventory_snapshot_id::bigint as inventory_snapshot_id,
    snapshot_date::date as snapshot_date,
    date_key::integer as date_key,
    market_key::smallint as market_key,
    product_key::integer as product_key,
    on_hand_units::integer as on_hand_units,
    in_transit_units::integer as in_transit_units,
    reorder_point_units::integer as reorder_point_units,
    stockout_flag::boolean as stockout_flag,
    estimated_lost_units::integer as estimated_lost_units,
    loaded_at::timestamp as loaded_at
from {{ source('raw', 'fact_inventory_snapshot') }}
