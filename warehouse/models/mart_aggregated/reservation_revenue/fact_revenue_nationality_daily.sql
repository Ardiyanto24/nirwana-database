-- Aturan kategorisasi (M5.1 §1.3 / M5.2 desain-skema-mart-aggregated.md): nationality
-- = 'Indonesia' -> Domestik (nationality_group_id 1), selain itu -> Mancanegara (id 2).
select
    b.property_id,
    case when g.nationality = 'Indonesia' then 1 else 2 end as nationality_group_id,
    b.check_in_date as period_date,
    count(*) as bookings_count,
    sum(b.total_amount) as revenue
from {{ ref('mart_cleaned__bookings') }} as b
left join {{ ref('mart_cleaned__guests') }} as g
    on b.guest_id = g.guest_id
where b.status in ('completed', 'confirmed')
group by 1, 2, 3
