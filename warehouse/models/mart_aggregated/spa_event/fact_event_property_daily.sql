select
    property_id,
    event_date as period_date,
    safe_divide(countif(status = 'cancelled'), count(*)) as cancellation_rate
from {{ ref('mart_cleaned__event_bookings') }}
group by 1, 2
