-- Flag product-market return-rate outliers with a minimum volume guardrail.
with product_rates as (
    select
        market_code,
        category,
        subcategory,
        sum(units_sold) as units_sold,
        sum(units_returned) as units_returned,
        sum(units_returned)::double precision / nullif(sum(units_sold), 0) as return_rate
    from operations.mart_product_returns
    group by market_code, category, subcategory
    having sum(units_sold) >= 100
),

benchmark as (
    select percentile_cont(0.75) within group (order by return_rate) as p75_return_rate
    from product_rates
)

select
    product_rates.*,
    benchmark.p75_return_rate
from product_rates
cross join benchmark
where product_rates.return_rate > benchmark.p75_return_rate
order by product_rates.return_rate desc, product_rates.units_sold desc;
