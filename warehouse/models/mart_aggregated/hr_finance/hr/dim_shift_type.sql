select
    row_number() over (order by shift_type) as shift_type_id,
    shift_type as shift_type_name
from (
    select distinct shift_type
    from {{ ref('mart_cleaned__staff_shifts') }}
    where shift_type is not null
)
