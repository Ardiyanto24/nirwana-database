select
    row_number() over (order by room_type) as room_type_id,
    room_type as room_type_name
from (
    select distinct room_type
    from {{ ref('mart_cleaned__bookings') }}
    where room_type is not null
)
