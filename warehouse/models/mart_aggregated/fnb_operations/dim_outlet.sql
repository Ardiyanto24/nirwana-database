select
    o.outlet_id,
    o.outlet_name,
    o.property_id,
    ot.outlet_type_id
from {{ ref('mart_cleaned__fnb_outlets') }} as o
left join {{ ref('dim_outlet_type') }} as ot
    on o.outlet_type = ot.outlet_type_name
