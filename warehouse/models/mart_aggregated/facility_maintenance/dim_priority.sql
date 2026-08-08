select
    row_number() over (order by priority) as priority_id,
    priority as priority_name
from (
    select distinct priority
    from {{ ref('mart_cleaned__maintenance_tickets') }}
    where priority is not null
)
