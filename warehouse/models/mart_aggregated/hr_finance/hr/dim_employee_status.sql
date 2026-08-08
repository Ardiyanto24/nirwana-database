select
    row_number() over (order by status) as status_id,
    status as status_name
from (
    select distinct status
    from {{ ref('mart_cleaned__employees') }}
    where status is not null
)
