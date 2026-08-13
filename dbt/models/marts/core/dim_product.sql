select
    product_key::integer as product_key,
    sku::text as sku,
    product_name::text as product_name,
    category::text as category,
    subcategory::text as subcategory,
    brand::text as brand,
    list_price_eur::double precision as list_price_eur,
    standard_cost_eur::double precision as standard_cost_eur,
    base_return_probability::double precision as base_return_probability,
    supplier_lead_time_days::integer as supplier_lead_time_days,
    weight_kg::double precision as weight_kg
from {{ source('raw', 'dim_product') }}
