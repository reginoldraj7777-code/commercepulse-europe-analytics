select
    date_key::integer as date_key,
    date::date as date,
    year::integer as year,
    quarter::text as quarter,
    month::integer as month_number,
    month_name::text as month_name,
    month_start::date as month_start,
    week_start::date as week_start,
    iso_week::integer as iso_week,
    day_name::text as day_name,
    is_weekend::boolean as is_weekend,
    is_month_end::boolean as is_month_end,
    is_european_holiday::boolean as is_european_holiday
from {{ source('raw', 'dim_date') }}
