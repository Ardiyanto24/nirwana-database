select
    row_number() over (order by service_name) as service_id,
    service_name
from (
    select distinct service_name
    from {{ ref('mart_cleaned__spa_bookings') }}
    where service_name is not null
)
