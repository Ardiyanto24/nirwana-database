-- avg_sla_duration_hours: nilai MENTAH (jam), TIDAK ada flag breach -- threshold SLA
-- per priority belum ditentukan (M5.1 "Kebutuhan Khusus kategori C" / Keputusan #7
-- decisions.md). pending_count = tiket open/in-progress, terpisah dari yang sudah resolved.
select
    property_id,
    fa.facility_area_id,
    it.issue_type_id,
    pr.priority_id,
    reported_date as period_date,
    count(*) as new_ticket_count,
    avg(
        case when status = 'resolved'
            then timestamp_diff(timestamp(resolved_date), timestamp(reported_date), hour)
        end
    ) as avg_sla_duration_hours,
    countif(status in ('open', 'in-progress')) as pending_count
from {{ ref('mart_cleaned__maintenance_tickets') }} as t
left join {{ ref('dim_facility_area') }} as fa
    on t.facility_area = fa.facility_area_name
left join {{ ref('dim_issue_type') }} as it
    on t.issue_type = it.issue_type_name
left join {{ ref('dim_priority') }} as pr
    on t.priority = pr.priority_name
group by 1, 2, 3, 4, 5
