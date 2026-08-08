select
    row_number() over (order by outlet_type) as outlet_type_id,
    outlet_type as outlet_type_name
from (
    select distinct outlet_type
    from {{ ref('mart_cleaned__fnb_outlets') }}
    where outlet_type is not null
)
