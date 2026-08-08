select
    v.venue_id,
    v.venue_name,
    v.property_id,
    vt.venue_type_id,
    v.max_capacity
from {{ ref('mart_cleaned__venues') }} as v
left join {{ ref('dim_venue_type') }} as vt
    on v.venue_type = vt.venue_type_name
