select
    row_number() over (order by facility_area) as facility_area_id,
    facility_area as facility_area_name
from (
    select distinct facility_area
    from {{ ref('mart_cleaned__maintenance_tickets') }}
    where facility_area is not null
)
