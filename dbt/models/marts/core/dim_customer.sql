select
    customer_key::bigint as customer_key,
    customer_id::text as customer_id,
    acquisition_date::date as acquisition_date,
    acquisition_date_key::integer as acquisition_date_key,
    home_market_key::smallint as home_market_key,
    acquisition_channel_key::smallint as acquisition_channel_key,
    customer_segment::text as customer_segment,
    loyalty_tier::text as loyalty_tier,
    marketing_consent::boolean as marketing_consent
from {{ source('raw', 'dim_customer') }}
