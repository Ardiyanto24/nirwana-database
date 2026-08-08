select
    row_number() over (order by booking_channel) as channel_id,
    booking_channel as channel_name
from (
    select distinct booking_channel
    from {{ ref('mart_cleaned__bookings') }}
    where booking_channel is not null
)
