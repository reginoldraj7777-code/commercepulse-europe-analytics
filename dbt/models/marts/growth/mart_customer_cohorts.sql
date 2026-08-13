with customer_orders as (
    select
        customer_key,
        date_trunc('month', order_ts)::date as order_month
    from {{ ref('int_order_finance') }}
    group by 1, 2
),

cohorted as (
    select
        customer_key,
        order_month,
        min(order_month) over (partition by customer_key) as cohort_month
    from customer_orders
),

indexed as (
    select
        *,
        (
            extract(year from age(order_month, cohort_month)) * 12
            + extract(month from age(order_month, cohort_month))
        )::integer as month_index
    from cohorted
),

counts as (
    select
        cohort_month,
        month_index,
        count(distinct customer_key) as active_customers
    from indexed
    where month_index between 0 and 12
    group by 1, 2
)

select
    counts.*,
    max(case when counts.month_index = 0 then counts.active_customers end)
        over (partition by counts.cohort_month) as cohort_size,
    {{ safe_divide(
        'active_customers',
        'max(case when month_index = 0 then active_customers end) over (partition by cohort_month)'
    ) }} as retention_rate
from counts
