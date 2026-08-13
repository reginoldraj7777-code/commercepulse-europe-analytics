select
    i.*,
    p.category,
    p.subcategory,
    p.list_price_eur,
    m.market_code,
    m.market_name,
    i.estimated_lost_units * p.list_price_eur as estimated_lost_revenue_eur
from {{ ref('stg_inventory_snapshot') }} as i
left join {{ ref('dim_product') }} as p using (product_key)
left join {{ ref('dim_market') }} as m using (market_key)
