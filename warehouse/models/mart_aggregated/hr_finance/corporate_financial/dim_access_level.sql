select
    row_number() over (order by access_level) as access_level_id,
    access_level as access_level_name
from (
    select distinct access_level
    from {{ ref('mart_cleaned__employees') }}
    where access_level is not null
)
