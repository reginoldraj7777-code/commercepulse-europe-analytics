select
    market_key::smallint as market_key,
    market_code::text as market_code,
    market_name::text as market_name,
    region_cluster::text as region_cluster,
    currency_code::text as currency_code,
    vat_rate::double precision as vat_rate,
    demand_weight::double precision as demand_weight,
    fulfillment_hub::text as fulfillment_hub
from {{ source('raw', 'dim_geography') }}
