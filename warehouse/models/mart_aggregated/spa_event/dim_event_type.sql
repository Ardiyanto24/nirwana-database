select
    row_number() over (order by event_type) as event_type_id,
    event_type as event_type_name
from (
    select distinct event_type
    from {{ ref('mart_cleaned__event_bookings') }}
    where event_type is not null
)
