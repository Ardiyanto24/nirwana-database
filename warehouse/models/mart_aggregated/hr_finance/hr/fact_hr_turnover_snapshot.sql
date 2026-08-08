-- Koreksi (M5.3): employees tidak punya tanggal resign/terminasi, cuma status akhir
-- -- turnover rate hanya bisa dihitung sebagai snapshot current-state, bukan tren
-- bulanan historis. Pola sama fact_facility_room_status_daily/fact_fnb_inventory_status.
select
    e.property_id,
    d.department_id,
    current_date() as period_date,
    safe_divide(countif(e.status != 'active'), count(*)) as turnover_rate
from {{ ref('mart_cleaned__employees') }} as e
left join {{ ref('dim_department') }} as d
    on e.department = d.department_name
group by 1, 2, 3
