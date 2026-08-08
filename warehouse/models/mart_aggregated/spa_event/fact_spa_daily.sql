with base as (
    select
        property_id,
        service_date as period_date,
        status,
        customer_type,
        price,
        date_diff(service_date, booking_date, day) as lead_time_days
    from {{ ref('mart_cleaned__spa_bookings') }}
)

select
    property_id,
    period_date,
    sum(case when status in ('completed', 'confirmed') then price else 0 end) as revenue,
    count(*) as booking_count,
    safe_divide(countif(customer_type = 'walk-in'), count(*)) as walk_in_ratio,
    avg(lead_time_days) as avg_lead_time_days,
    approx_quantiles(lead_time_days, 2)[offset(1)] as median_lead_time_days,
    safe_divide(countif(status = 'cancelled'), count(*)) as cancellation_rate
from base
group by 1, 2
