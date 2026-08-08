-- dim_room: room_id natural key. Dipakai lintas domain (Revenue, Facility/Ops).
select
    r.room_id,
    r.property_id,
    rt.room_type_id
from {{ ref('mart_cleaned__rooms') }} as r
left join {{ ref('dim_room_type') }} as rt
    on r.room_type = rt.room_type_name
