select
    session_id::bigint as session_id,
    session_ts::timestamp as session_ts,
    date_key::integer as date_key,
    customer_key::bigint as customer_key,
    market_key::smallint as market_key,
    channel_key::smallint as channel_key,
    campaign_key::integer as campaign_key,
    device_type::text as device_type,
    page_load_ms::integer as page_load_ms,
    product_views::integer as product_views,
    added_to_cart::boolean as added_to_cart,
    checkout_started::boolean as checkout_started,
    converted_order_id::bigint as converted_order_id,
    loaded_at::timestamp as loaded_at,
    is_late_arrival::boolean as is_late_arrival
from {{ source('raw', 'fact_sessions') }}
