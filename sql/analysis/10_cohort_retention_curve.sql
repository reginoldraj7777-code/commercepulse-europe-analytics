-- Weighted retention curve across eligible purchasing cohorts.
select
    month_index,
    sum(active_customers)::double precision / nullif(sum(cohort_size), 0)
        as weighted_retention_rate,
    sum(active_customers) as active_customers,
    sum(cohort_size) as eligible_cohort_customers
from growth.mart_customer_cohorts
group by month_index
order by month_index;
